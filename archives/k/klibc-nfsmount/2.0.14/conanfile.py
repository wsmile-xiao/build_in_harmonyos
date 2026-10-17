#!/usr/bin/env python3
"""Conan recipe for klibc-nfsmount 2.0.14 — NFS mount utility (klibc usr/kinit/nfsmount).

klibc-nfsmount is the standalone ``nfsmount`` tool shipped inside the klibc
source tree (``usr/kinit/nfsmount``): it performs the portmap/mountd RPC
negotiation and finally invokes ``mount(2)`` with ``struct nfs_mount_data``
to mount an NFS share. Upstream builds it with the kernel-style kbuild system
against the klibc libc itself; this recipe instead compiles the five upstream
sources directly against the OHOS system libc (musl-based), which is the
sensible adaptation for a HarmonyOS PC tool (zero external dependencies).

OHOS adaptation notes:
- The OHOS SDK UAPI copy of ``<linux/nfs_mount.h>`` includes ``<linux/in.h>``
  which pulls in ``<linux/socket.h>``; that header unconditionally redefines
  ``struct sockaddr_storage`` already provided by musl's ``<sys/socket.h>``
  (the kernel ``libc-compat.h`` guards only trigger with glibc). The build
  therefore generates a shadow ``compat/linux/nfs_mount.h`` (verbatim UAPI
  struct + flags, minus the conflicting include chain) and compiles with
  ``-I compat`` ahead of the sysroot.
- musl does not provide ``bindresvport()`` (BSD/glibc helper used by the
  portmap client). The build generates ``compat/portability.h`` with a static
  inline fallback adapted from klibc's own ``usr/klibc/inet/bindresvport.c``;
  the source patches include it from mount.c/sunrpc.c.
- Small portability patches: missing ``<stddef.h>`` (offsetof),
  ``<unistd.h>`` (read/write/close) and ``socklen_t`` for recvfrom().
- Upstream test suite (R51): the klibc tree ships 39 test programs under
  ``usr/klibc/tests``; build() compiles each one against the published
  ``klibc/2.0.14`` package (``tool_requires``, build-time only — the shipped
  nfsmount binary links the OHOS musl libc and does not depend on klibc at
  runtime) and executes them, recording per-test results in the build log.
"""
import os
import re
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout

# conan arch -> OHOS clang target triple (only triples shipped by the SDK)
_TARGET_TRIPLE = {
    "armv8": "aarch64-linux-ohos",
    "armv7": "arm-linux-ohos",
    "x86_64": "x86_64-linux-ohos",
}

# Sources compiled into the nfsmount binary (upstream Kbuild objs list)
_NFSMOUNT_SRCS = ["main.c", "mount.c", "portmap.c", "dummypmap.c", "sunrpc.c"]
_NFSMOUNT_SRCS_SANS_EXT = [os.path.splitext(s)[0] for s in _NFSMOUNT_SRCS]

# Per-test compile flags from the upstream Kbuild (usr/klibc/tests/Kbuild):
# testvsnp exercises printf formats gcc does not know; malloctest3 calls
# malloc() with deliberately unreasonably large values; strsearch must not
# have its string calls replaced by compiler builtins.
_UPSTREAM_TEST_CFLAGS = {
    "testvsnp": ["-Wno-format"],
    "malloctest3": ["-Wno-alloc-size-larger-than"],
    "strsearch": [
        "-fno-builtin-strchr", "-fno-builtin-strrchr",
        "-fno-builtin-strspn", "-fno-builtin-strcspn",
        "-fno-builtin-strpbrk", "-fno-builtin-strstr",
    ],
}

# Tests that need command line arguments (upstream ships no runtests script;
# same harness as the merged klibc/2.0.14 main package): fnmatch takes
# pattern/string/flags (with argv[1]=NULL it would crash); mmaptest takes a
# writable scratch path (upstream hardcodes /tmp which is read-only on OHOS,
# E002).


class KlibcNfsmountConan(ConanFile):
    name = "klibc-nfsmount"
    version = "2.0.14"
    description = (
        "nfsmount — small NFS mount utility from the klibc project "
        "(portmap/mountd RPC negotiation + mount(2) with struct nfs_mount_data)"
    )
    license = "MIT AND BSD-3-Clause AND GPL-2.0-only"
    homepage = "https://www.kernel.org/pub/linux/libs/klibc/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("nfs", "mount", "klibc", "rpc")

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 零外部库依赖：仅 libc + Linux UAPI 头（OHOS SDK sysroot 提供）。
        pass

    def build_requirements(self):
        # 上游测试套件（usr/klibc/tests）的链接目标是 klibc 本体（crt0.o +
        # libklibc.a），不是系统 musl。交付物 nfsmount 动态链接 OHOS musl，
        # 运行时不依赖 klibc —— klibc 仅是构建/测试期的链接目标，故用
        # tool_requires（不向消费者传播；klibc/2.0.14 已发布到制品仓，R36）。
        self.tool_requires("klibc/2.0.14")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ---- helpers ----

    def _compiler(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return compilers.get("c", "clang") if compilers else "clang"

    def _target_triple(self):
        arch = str(self.settings.arch)
        if arch not in _TARGET_TRIPLE:
            raise ConanInvalidConfiguration(
                f"klibc-nfsmount: unsupported architecture '{arch}' "
                f"(supported: {', '.join(sorted(_TARGET_TRIPLE))})"
            )
        return _TARGET_TRIPLE[arch]

    def _find_sysroot(self, cc):
        """Locate the OHOS SDK sysroot.

        OHOS clang does not support ``--print-sysroot``; derive it from
        ``--print-resource-dir`` (…/native/llvm/lib/clang/<ver> → up 4 levels
        → native/sysroot), with fallbacks (same approach as the klibc recipe).
        """
        try:
            rd = subprocess.check_output(
                [cc, "--print-resource-dir"], text=True, stderr=subprocess.DEVNULL
            ).strip()
            if rd:
                d = os.path.normpath(rd)
                for _ in range(4):
                    d = os.path.dirname(d)
                sr = os.path.join(d, "sysroot")
                if os.path.isdir(os.path.join(sr, "usr", "include")):
                    return sr
        except Exception:
            pass
        try:
            out = subprocess.check_output(
                [cc, "--print-sysroot"], text=True, stderr=subprocess.DEVNULL
            ).strip()
            if out and os.path.isdir(os.path.join(out, "usr", "include")):
                return out
        except Exception:
            pass
        return None

    def _write_compat_headers(self, compat_dir, cc):
        """Generate the OHOS compatibility headers into the build folder.

        1. ``linux/nfs_mount.h`` — shadow of the SDK UAPI header: same struct
           and flag definitions, but ``struct sockaddr_in`` is taken from
           ``netinet/in.h`` and the ``<linux/in.h>`` include (which would drag
           in the musl-conflicting ``<linux/socket.h>``) is dropped.
        2. ``portability.h`` — static inline ``bindresvport()`` fallback for
           musl-based libcs, adapted from klibc usr/klibc/inet/bindresvport.c.
        """
        sysroot = self._find_sysroot(cc)
        if not sysroot:
            raise ConanInvalidConfiguration(
                "OHOS sysroot not found; klibc-nfsmount needs Linux UAPI "
                "headers (linux/nfs.h etc.) from the OHOS SDK sysroot"
            )
        uapi = os.path.join(sysroot, "usr", "include", "linux", "nfs_mount.h")
        if not os.path.isfile(uapi):
            raise ConanInvalidConfiguration(
                f"Linux UAPI header not found: {uapi}"
            )

        os.makedirs(os.path.join(compat_dir, "linux"), exist_ok=True)

        with open(uapi, "r", errors="replace") as f:
            body = f.read()
        # Strip the include block AND the original include guard (the shim adds
        # its own); keeping the inner guard would make the already-defined
        # macro skip the entire body (struct definitions vanish).
        body = re.sub(r"^#include .*$", "", body, flags=re.M)
        body = re.sub(r"^#ifndef _LINUX_NFS_MOUNT_H.*$", "", body, flags=re.M)
        body = re.sub(r"^#define _LINUX_NFS_MOUNT_H.*$", "", body, flags=re.M)
        body = re.sub(r"^#endif(\s*/\*.*\*/)?\s*$", "", body, flags=re.M)

        shim = os.path.join(compat_dir, "linux", "nfs_mount.h")
        with open(shim, "w") as f:
            f.write(
                "/* Shadow <linux/nfs_mount.h> for OHOS (musl-based libc).\n"
                " * Generated by the klibc-nfsmount conan recipe from the SDK\n"
                " * UAPI header; struct/flag definitions are verbatim. The\n"
                " * <linux/in.h> include is dropped (its <linux/socket.h>\n"
                " * redefines sockaddr_storage already provided by musl's\n"
                " * <sys/socket.h>) and struct sockaddr_in comes from\n"
                " * <netinet/in.h> instead (ABI-identical layout).\n */\n"
                "#ifndef _LINUX_NFS_MOUNT_H\n"
                "#define _LINUX_NFS_MOUNT_H\n"
                "#include <linux/nfs.h>\n"
                "#include <linux/nfs2.h>\n"
                "#include <linux/nfs3.h>\n"
                "#include <netinet/in.h>\n"
                + body
                + "\n#endif /* _LINUX_NFS_MOUNT_H */\n"
            )

        portability = os.path.join(compat_dir, "portability.h")
        with open(portability, "w") as f:
            f.write(
                "/* bindresvport() fallback for musl-based libcs (e.g. OHOS),\n"
                " * adapted from klibc usr/klibc/inet/bindresvport.c. */\n"
                "#ifndef NFSMOUNT_PORTABILITY_H\n"
                "#define NFSMOUNT_PORTABILITY_H\n"
                "#include <errno.h>\n"
                "#include <string.h>\n"
                "#include <sys/socket.h>\n"
                "#include <sys/types.h>\n"
                "#include <netinet/in.h>\n"
                "#include <unistd.h>\n"
                "#ifndef IPPORT_RESERVED\n"
                "#define IPPORT_RESERVED 1024\n"
                "#endif\n"
                "static inline int bindresvport(int sd, struct sockaddr_in *sin)\n"
                "{\n"
                "    struct sockaddr_in me;\n"
                "    static short port;\n"
                "    int ret = -1;\n"
                "    int i;\n"
                "    if (sin == NULL) {\n"
                "        memset(&me, 0, sizeof(me));\n"
                "        sin = &me;\n"
                "        sin->sin_family = AF_INET;\n"
                "    } else if (sin->sin_family != AF_INET) {\n"
                "        errno = EPFNOSUPPORT;\n"
                "        return -1;\n"
                "    }\n"
                "    if (port == 0)\n"
                "        port = 600 + (getpid() % 400);\n"
                "    for (i = 0; i < 400; i++, port++) {\n"
                "        if (port >= IPPORT_RESERVED)\n"
                "            port = 600;\n"
                "        sin->sin_port = htons(port);\n"
                "        ret = bind(sd, (struct sockaddr *)sin, sizeof(*sin));\n"
                "        if (ret != -1)\n"
                "            break;\n"
                "    }\n"
                "    return ret;\n"
                "}\n"
                "#endif /* NFSMOUNT_PORTABILITY_H */\n"
            )
        return compat_dir

    # ---- conan stages ----

    def build(self):
        apply_conandata_patches(self)
        cc = self._compiler()
        triple = self._target_triple()
        src = self.source_folder
        nfssrc = os.path.join(src, "usr", "kinit", "nfsmount")
        if not os.path.isdir(nfssrc):
            raise ConanInvalidConfiguration(
                f"nfsmount sources not found in the klibc tree: {nfssrc}"
            )

        compat_dir = self._write_compat_headers(
            os.path.join(self.build_folder, "compat"), cc
        )

        # R51 上游测试链接目标：tool_requires 的 klibc/2.0.14 包。
        dep = self.dependencies.build["klibc"].cpp_info
        libdir = dep.libdirs[0]
        for f in ("crt0.o", "libklibc.a"):
            if not os.path.isfile(os.path.join(libdir, f)):
                raise ConanInvalidConfiguration(
                    f"klibc package artifact missing for upstream tests: {f}"
                )
        testdir = os.path.join(src, "usr", "klibc", "tests")
        if not os.path.isdir(testdir):
            self.output.warning("usr/klibc/tests not found: upstream tests skipped")

        # 全部编译/链接/测试运行收拢进一个 bash 脚本。conan 的 self.run 会
        # 经 /bin/sh（mksh）中转，而本设备对 python/mksh 祖先链上的 clang-15
        # exec 有分钟级窗口的静默拒绝（CI_RUN.md §5.2 R7 弹窗变体）；实测
        # python→bash（list 直连，无 mksh 层）→脚本内 bash 子进程拉起 clang
        # 全天稳定，故此处不用 self.run，而用 subprocess 直连 bash，
        # conanbuild 环境由脚本自行 source。结果如实记录到摘要/日志。
        script = self._write_build_script(
            cc, triple, compat_dir, libdir, dep.includedirs, testdir
        )
        self._run_build_script(script)

        binary = os.path.join(self.build_folder, "nfsmount")
        if not os.path.isfile(binary):
            raise ConanException("nfsmount binary was not produced by build.sh")
        self._report_upstream_tests()

    def _run_build_script(self, script):
        """Run build.sh as a direct bash child (no mksh wrapper) and surface
        the per-test markers plus any warnings in the conan log; the full
        output (test stdout incl. non-UTF-8 bytes) is kept in
        upstream-tests-full.log next to the build artifacts.
        """
        bash = "/data/service/hnp/bin/bash"
        if not os.path.isfile(bash):
            import shutil

            bash = shutil.which("bash") or "bash"
        r = subprocess.run(
            [bash, script], cwd=self.build_folder, capture_output=True
        )
        full_log = os.path.join(self.build_folder, "upstream-tests-full.log")
        with open(full_log, "wb") as f:
            f.write(r.stdout)
            f.write(r.stderr)
        text = (r.stdout + b"\n" + r.stderr).decode("utf-8", errors="replace")
        for line in text.splitlines():
            if (
                line.startswith("UPSTREAM_TEST")
                or line.startswith("WARNING")
                or line.startswith("clang probe")
            ):
                self.output.info(line)
        if r.returncode != 0:
            self.output.error(text[-2000:])
            raise ConanException(
                f"build.sh failed (rc={r.returncode}); full log: {full_log}"
            )

    def _write_build_script(self, cc, triple, compat_dir, libdir, incdirs, testdir):
        """Generate build.sh: nfsmount build (fail-fast) + the upstream test
        suite (compile, link and run each klibc test program).

        Every compiler/test invocation is a direct child of this bash script
        (see the exec-authorization note in build()). Failures of individual
        upstream tests are recorded but do not fail the build (same policy as
        the merged klibc/2.0.14 main package); reasons go to notes.md/PR.
        """
        conanbuild = os.path.join(
            self.generators_folder or self.build_folder, "conanbuild.sh"
        )
        bf = self.build_folder
        src = self.source_folder
        outdir = os.path.join(bf, "upstream-tests")
        mmap_tmp = os.path.join(outdir, "mmaptest.tmp")
        names = sorted(
            os.path.splitext(f)[0]
            for f in (os.listdir(testdir) if os.path.isdir(testdir) else [])
            if f.endswith(".c")
        )
        run_args = {
            # 注意：bash 变量展开不会去除引号，故这里不写内层引号；
            # 通配符由脚本里的 set -f（noglob）保护。
            "fnmatch": "*.c foo.c 0",
            "mmaptest": f"{mmap_tmp}",
        }
        lines = [
            "#!/data/service/hnp/bin/bash",
            "# Generated by conanfile.py (klibc-nfsmount) - do not edit.",
            "#",
            "# OHOS exec-authorization note (CI_RUN.md §5.2, R7 popup variant):",
            "# clang-15 execs whose *immediate caller* is python or mksh are",
            "# transiently denied (silent rc=1); spawns rooted in a bash process",
            "# are always permitted. All compiler/test invocations therefore run",
            "# as children of this script; conan only spawns `bash build.sh`.",
            "",
            "set -e",
            f'. "{conanbuild}"',
            f'CC="{cc}"',
            f'TRIPLE="{triple}"',
            f'BF="{bf}"',
            f'SRC="{src}"',
            f'COMPAT="{compat_dir}"',
            f'KLIBC_LIB="{libdir}"',
            f'TESTS_SRC="{testdir}"',
            f'OUT="{outdir}"',
            'SUMMARY="$BF/upstream-tests-summary.txt"',
            'mkdir -p "$OUT"',
            "",
            "# clang 可执行性探测（R7 弹窗变体下 exec 授权有分钟级窗口波动，重试等待窗口）",
            "cc_probe() { local out; out=$(\"$CC\" \"$@\" 2>/dev/null) || return 1; printf '%s' \"$out\"; }",
            "BUILTINS=\"\"",
            "for i in 1 2 3 4 5; do",
            '  BUILTINS=$(cc_probe -print-libgcc-file-name) && [ -n "$BUILTINS" ] && break',
            '  echo \"clang probe attempt $i failed, sleep 3s\"',
            "  sleep 3",
            "done",
            '[ -n "$BUILTINS" ] || { echo \"clang not executable\"; exit 1; }',
            'CLANG_INC=$(cc_probe --print-file-name=include)',
            f'KLIBC_INC="{" ".join(incdirs)}"',
            'INC=""',
            'for d in $KLIBC_INC; do INC="$INC -isystem $d"; done',
            'INC="$INC -isystem $CLANG_INC"',
            "TEST_BASE=\"--target=$TRIPLE -nostdlib -nostdinc $INC "
            "-D__KLIBC__=2 -D__KLIBC_MINOR__=0 -D_BITSIZE=64 -static\"",
            'TEST_LINK="$KLIBC_LIB/crt0.o -Wl,--start-group '
            '$KLIBC_LIB/libklibc.a $BUILTINS -Wl,--end-group"',
            "build_and_run() {",
            '  local name="$1" ccmd="$2" rargs="$3" prog rc',
            '  prog="$OUT/$name"',
            "  if ! $ccmd; then",
            "    sleep 2",
            "    if ! $ccmd; then",
            '      echo "UPSTREAM_TEST BUILD-FAIL $name"',
            '      echo "BUILD-FAIL $name" >> "$SUMMARY"',
            "      return",
            "    fi",
            "  fi",
            "  rc=0",
            '  timeout 15 "$prog" $rargs || rc=$?',
            "  if [ $rc -ne 0 ]; then",
            "    sleep 2",
            '    timeout 15 "$prog" $rargs || rc=$?',
            "  fi",
            "  if [ $rc -eq 0 ]; then",
            '    echo "PASS $name" >> "$SUMMARY"',
            '    echo "UPSTREAM_TEST PASS $name"',
            "  else",
            '    echo "FAIL $name rc=$rc" >> "$SUMMARY"',
            '    echo "UPSTREAM_TEST FAIL $name rc=$rc"',
            "  fi",
            "}",
            "",
            "# ---- deliverable: nfsmount (fail-fast) ----",
            f'for s in {" ".join(_NFSMOUNT_SRCS_SANS_EXT)}; do',
            '  "$CC" --target=$TRIPLE -O2 -Wall -I"$COMPAT" '
            '-c "$SRC/usr/kinit/nfsmount/$s.c" -o "$BF/$s.o"',
            "done",
            'LINK_LINE=""',
            f'for s in {" ".join(_NFSMOUNT_SRCS_SANS_EXT)}; do LINK_LINE="$LINK_LINE $BF/$s.o"; done',
            '"$CC" --target=$TRIPLE $LINK_LINE -o "$BF/nfsmount"',
            "",
            "# ---- upstream tests (R51) ----",
            "set +e",
            "set -f",
            ': > "$SUMMARY"',
        ]
        for name in names:
            flags = " ".join(_UPSTREAM_TEST_CFLAGS.get(name, []))
            ccmd = (
                f"$CC $TEST_BASE {flags} $TESTS_SRC/{name}.c "
                f"$TEST_LINK -o $OUT/{name}"
            )
            rargs = run_args.get(name)
            if rargs:
                # 整体加引号作为一个参数传入，函数内再按词展开（set -f 防止通配符展开）
                lines.append(f'build_and_run {name} "{ccmd}" "{rargs}"')
            else:
                lines.append(f'build_and_run {name} "{ccmd}"')
        lines.append('echo "UPSTREAM_TESTS_DONE"')
        script = os.path.join(bf, "build.sh")
        with open(script, "w") as f:
            f.write("\n".join(lines) + "\n")
        return script

    def _report_upstream_tests(self):
        """Read upstream-tests-summary.txt written by build.sh and report."""
        summary = os.path.join(self.build_folder, "upstream-tests-summary.txt")
        if not os.path.isfile(summary):
            self.output.warning("upstream test summary not found")
            return
        passed, failed, build_failed = [], [], []
        with open(summary) as f:
            for line in f:
                parts = line.split()
                if not parts:
                    continue
                if parts[0] == "PASS":
                    passed.append(parts[1])
                elif parts[0] == "FAIL":
                    failed.append(parts[1])
                elif parts[0] == "BUILD-FAIL":
                    build_failed.append(parts[1])
        total = len(passed) + len(failed) + len(build_failed)
        self.output.info(
            f"upstream tests: {len(passed)} passed, {len(failed)} failed, "
            f"{len(build_failed)} build-failed (total {total})"
        )
        if failed:
            self.output.warning(f"failed tests: {' '.join(failed)}")
        if build_failed:
            self.output.warning(f"build-failed tests: {' '.join(build_failed)}")

    def package(self):
        bin_dst = os.path.join(self.package_folder, "bin")
        lic_dst = os.path.join(self.package_folder, "licenses")
        copy(self, "nfsmount", self.build_folder, bin_dst)
        # klibc 树内许可文件（nfsmount 无独立 LICENSE，随 klibc 项目许可）。
        copy(
            self,
            "LICENSE",
            os.path.join(self.source_folder, "usr", "klibc"),
            lic_dst,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
