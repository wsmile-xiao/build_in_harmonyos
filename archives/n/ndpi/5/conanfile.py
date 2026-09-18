#!/usr/bin/env python3
"""Conan recipe — ndpi 5 (Autotools).

nDPI is the ntop open source deep packet inspection library.
Upstream tag 5.0 (AC_INIT 5.0.0); archive dir keeps task version "5",
artifact version normalized to "5.0" via set_version() (E563).
"""

import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout

# install(1) shim for filesystems without chmod/hardlink support
# (same pattern as the aircrack-ng 1.7 recipe: mode flags are ignored,
# files are copied with cp(1), directories created with mkdir -p).
_INSTALL_SHIM = r"""#!/bin/sh
# install(1) shim for the HarmonyOS PC target filesystem
# (hmbs capabilities: chmod=0, hardlink=0).
# Mode flags are ignored (chmod unsupported); files are copied with
# cp(1), directories are created with mkdir -p.
is_dir=0
mk_leading=0
files=
while [ "$#" -gt 0 ]; do
  case "$1" in
    -d) is_dir=1 ;;
    -D) mk_leading=1 ;;
    -m) shift ;;
    -m?*|--mode=*) ;;
    -c|-p|-v|-s) ;;
    -g|-o|-t) shift ;;
    --) shift
        while [ "$#" -gt 0 ]; do files="$files $1"; shift; done
        break ;;
    -*) ;;
    *) files="$files $1" ;;
  esac
  shift
done

[ -z "$files" ] && exit 0

if [ "$is_dir" = 1 ]; then
  for d in $files; do mkdir -p "$d" || exit 1; done
  exit 0
fi

set -- $files
count=$#
[ "$count" -lt 2 ] && exit 0
if [ "$count" -ge 3 ]; then
  eval "dest=\${$count}"
  mkdir -p "$dest" || exit 1
elif [ "$mk_leading" = 1 ]; then
  eval "dest=\${$count}"
  mkdir -p "$(dirname "$dest")" || exit 1
fi
cp -f "$@" || exit 1
exit 0
"""


class NdpiConan(ConanFile):
    name = "ndpi"
    # NOTE(dir-vs-artifact, E563): 归档目录保持任务卡版本 "5"（过 L0n
    # 分支门禁 feat/ndpi-5 精确匹配）；制品版本经 set_version() 归一化为
    # 上游 release tag "5.0"，满足 Conan >=2 字符版本校验。
    # 此处不得写字面 version = "5"（conan create 导出阶段必报
    # Invalid package version '5'）。
    description = "Open source deep packet inspection (DPI) library"
    license = "LGPL-3.0-or-later"
    homepage = "https://www.ntop.org/products/deep-packet-inspection/ndpi/"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def set_version(self):
        # 目录版本 "5" 仅用于归档路径/分支；制品版本取上游 tag 5.0
        #（== AC_INIT 5.0.0 的 release 标识），满足 Conan 版本校验正则
        # ^[a-z0-9_][a-z0-9_+.-]{1,100}$（总长 >= 2）。
        self.version = "5.0"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # example/ndpiReader and upstream tests/do.sh need libpcap.
        self.requires("libpcap/1.10.6")

    def build_requirements(self):
        # Release tarball ships no pre-generated configure; autoreconf it.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        else:
            tc.configure_args.append("--disable-static")
            tc.configure_args.append("--enable-shared")
        # Position-independent code is mandatory on this platform.
        tc.extra_cflags.append("-fPIC")
        tc.extra_cxxflags.append("-fPIC")
        tc.generate()
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()

    def _patch_config_for_ohos(self):
        """Teach config.guess/config.sub to recognize HarmonyOS."""
        candidates = [self.source_folder]
        cg_path = cs_path = None
        for d in candidates:
            cg = os.path.join(d, "config.guess")
            cs = os.path.join(d, "config.sub")
            if os.path.exists(cg) and os.path.exists(cs):
                cg_path, cs_path = cg, cs
                break
        if not cg_path:
            return
        self._patch_config_guess(cg_path)
        self._patch_config_sub(cs_path)

    def _patch_config_guess(self, cg_path):
        with open(cg_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        changed = False
        if "__OHOS__" not in content:
            old = "#if defined(__ANDROID__)\n    LIBC=android"
            new = ("#if defined(__ANDROID__)\n    LIBC=android"
                   "\n#elif defined(__OHOS__)\n    LIBC=ohos")
            if old in content:
                content = content.replace(old, new, 1)
                changed = True
        if "HarmonyOS" not in content:
            block = (
                "    *:HarmonyOS:*:*)\n"
                "\tcase \"$UNAME_MACHINE\" in\n"
                "\t    aarch64|arm64) MACHINE=aarch64 ;;\n"
                "\t    armv7*|armv8*) MACHINE=arm ;;\n"
                "\t    x86_64|amd64)  MACHINE=x86_64 ;;\n"
                "\t    i?86)          MACHINE=i686 ;;\n"
                "\t    *)            MACHINE=\"$UNAME_MACHINE\" ;;\n"
                "\tesac\n"
                "\tGUESS=${MACHINE}-unknown-linux-ohos\n"
                "\t;;\n\n"
                "    *:NetBSD:*:*)"
            )
            if "    *:NetBSD:*:*)" in content:
                content = content.replace("    *:NetBSD:*:*)", block, 1)
                changed = True
        if changed:
            with open(cg_path, "w", encoding="utf-8") as f:
                f.write(content)

    def _patch_config_sub(self, cs_path):
        with open(cs_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        changed = False
        if "ohos-linux" not in content:
            pattern = (r"(android-linux\)\s*\n\s*basic_machine=\$field1-unknown"
                       r"\s*\n\s*basic_os=linux-android\s*\n\s*;;\s*\n)")
            replacement = (r"\1\tohos-linux)\n"
                           r"\tbasic_machine=$field1-unknown\n"
                           r"\tbasic_os=linux-ohos\n\t;;\n")
            new_content, count = re.subn(pattern, replacement, content)
            if count > 0:
                content = new_content
                changed = True
        if changed:
            with open(cs_path, "w", encoding="utf-8") as f:
                f.write(content)

    def _patch_configure_tmpdir(self):
        """Redirect autoconf temp dirs to TMPDIR (read-only build roots)."""
        configure_path = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure_path):
            return
        with open(configure_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        original = content
        content = content.replace(
            "tmp=`(umask 077 && mktemp -d \"./confXXXXXX\") 2>/dev/null`",
            "tmp=`(mktemp -d \"${TMPDIR:-/tmp}/confXXXXXX\") 2>/dev/null`",
        )
        content = content.replace(
            "tmp=./conf$$-$RANDOM\n  (umask 077 && mkdir \"$tmp\")",
            "tmp=\"${TMPDIR:-/tmp}/conf$$-$RANDOM\"\n  mkdir \"$tmp\"",
        )
        if content != original:
            with open(configure_path, "w", encoding="utf-8") as f:
                f.write(content)

    def _patch_configure_pwd(self):
        """Fall back to $PWD when getcwd() is unavailable."""
        configure_path = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure_path):
            return
        with open(configure_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        original = content
        content = content.replace(
            "ac_pwd=`pwd` && test -n \"$ac_pwd\" &&",
            "ac_pwd=`pwd` 2>/dev/null || ac_pwd=$PWD\n"
            "test -n \"$ac_pwd\" &&",
        )
        content = content.replace(
            "if (pwd) >/dev/null 2>&1 && test -n \"`pwd`\"",
            "if (pwd) >/dev/null 2>&1 || test -n \"$PWD\"",
        )
        if content != original:
            with open(configure_path, "w", encoding="utf-8") as f:
                f.write(content)
        else:
            self.output.warning(
                "configure pwd-check pattern not found; relying on PWD env"
            )

    def _patch_one_tmpdir(self, path):
        """Redirect hardcoded /tmp/reader.* in upstream test scripts to TMPDIR."""
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except OSError:
            return False
        if "/tmp/reader." not in content:
            return False
        content = content.replace("/tmp/reader.", "${TMPDIR:-/tmp}/reader.")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        self.output.info("patched TMPDIR tmpfile root in %s" % path)
        return True

    def _patch_tests_tmpdir(self, root):
        """Patch upstream test scripts under root to honor TMPDIR (readonly /tmp)."""
        candidates = [
            os.path.join(root, "tests", "do.sh.in"),
            os.path.join(root, "tests", "do.sh"),
            os.path.join(root, "tests", "do-dga.sh"),
            os.path.join(root, "tests", "do-unit.sh"),
        ]
        seen = set()
        for cand in candidates:
            if os.path.isfile(cand):
                self._patch_one_tmpdir(cand)
                seen.add(cand)
        for dirpath, _dirs, files in os.walk(root):
            if "do.sh" in files:
                cand = os.path.join(dirpath, "do.sh")
                if cand not in seen and os.path.isfile(cand):
                    self._patch_one_tmpdir(cand)

    def build(self):
        apply_conandata_patches(self)

        os.environ["PWD"] = self.build_folder

        pkg_config = shutil.which("pkg-config")
        if pkg_config:
            real_path = os.path.realpath(pkg_config)
            prefix = os.path.dirname(os.path.dirname(real_path))
            aclocal_dir = os.path.join(prefix, "share", "aclocal")
            if os.path.isfile(os.path.join(aclocal_dir, "pkg.m4")):
                existing = os.environ.get("ACLOCAL_PATH", "")
                os.environ["ACLOCAL_PATH"] = (
                    "%s:%s" % (aclocal_dir, existing) if existing else aclocal_dir
                )

        # The GitHub archive ships autogen.sh + configure.ac but no
        # pre-generated configure; generate it the supported way.
        self.run("autoreconf -fiv", cwd=self.source_folder)

        self._patch_config_for_ohos()
        self._patch_configure_tmpdir()
        self._patch_configure_pwd()
        # Upstream tests/do.sh.in hardcodes /tmp/reader.$$.out (readonly on HMDFS).
        # Redirect the template before configure so generated do.sh inherits it.
        self._patch_tests_tmpdir(self.source_folder)

        autotools = Autotools(self)
        autotools.configure()
        # configure generates tests/do.sh from do.sh.in in the build tree;
        # patch generated copies too (out-of-source build-release layout).
        self._patch_tests_tmpdir(self.build_folder)
        self._patch_tests_tmpdir(self.source_folder)
        _tmpdir = os.environ.get("TMPDIR") or os.environ.get("TMP")
        if _tmpdir:
            try:
                os.makedirs(_tmpdir, exist_ok=True)
            except OSError:
                pass
        autotools.make(args=["-j1"])
        self._run_upstream_checks()

    def _run_upstream_checks(self):
        """Run upstream `make check` and emit the HMBS evidence marker.

        Upstream TESTS (tests/Makefile.am): do.sh (ndpiReader pcap replay
        over tests/cfgs/*/pcap), do-dga.sh (DGA accuracy/precision/recall
        gates), plus do-unit.sh only when json-c enables BUILD_UNITTESTS.
        Results are automake PASS/FAIL/SKIP lines; per-pcap OK/ERROR lines
        live inside do.sh output and the ctest-style log below.
        """
        log = os.path.join(self.build_folder, "make-check.log")
        cmd = "set -o pipefail; make check -j1 2>&1 | tee \"%s\"" % log
        try:
            self.run(cmd, cwd=self.build_folder, env="conanbuild")
        except Exception:
            pass

        discovered = executed = passed = failed = skipped = 0
        if os.path.isfile(log):
            with open(log, encoding="utf-8", errors="replace") as f:
                for line in f:
                    m = re.match(
                        r"^(PASS|FAIL|SKIP|XFAIL|XPASS|ERROR):\s+(\S+)",
                        line.strip(),
                    )
                    if not m:
                        continue
                    kind = m.group(1)
                    discovered += 1
                    executed += 1
                    if kind == "PASS":
                        passed += 1
                    elif kind in ("FAIL", "ERROR"):
                        failed += 1
                    elif kind == "XPASS":
                        failed += 1
                    else:
                        skipped += 1

        if failed == 0 and discovered > 0:
            status = "passed"
        elif failed > 0:
            status = "failed"
        else:
            status = "no_tests"
        marker = {
            "status": status,
            "framework": "automake",
            "command": "make check",
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False)
        )
        # Dual-channel emit + persist: build() is skipped on Conan cache hits,
        # so test_package re-emits this file every round (else evidence goes
        # missing -> incomplete). Same pattern as balloon 1.1.1 / balboa 2.1.2.
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False))
        try:
            os.makedirs(self.build_folder, exist_ok=True)
            with open(
                os.path.join(self.build_folder, "upstream_test_result.json"),
                "w",
                encoding="utf-8",
            ) as f:
                json.dump(marker, f, ensure_ascii=False)
        except OSError as e:
            self.output.warning("write upstream_test_result.json failed: %s" % e)
        if failed > 0 or discovered == 0:
            for dirpath, _dirs, files in os.walk(self.build_folder):
                if "test-suite.log" in files:
                    suite_log = os.path.join(dirpath, "test-suite.log")
                    self.output.info("TSLOG-FILE: " + suite_log)
                    try:
                        with open(suite_log, encoding="utf-8", errors="replace") as f:
                            for line in f:
                                self.output.info("TSLOG: " + line.rstrip("\n"))
                    except OSError:
                        pass
            if os.path.isfile(log):
                try:
                    with open(log, encoding="utf-8", errors="replace") as f:
                        for line in f:
                            s = line.strip()
                            if "ERROR" in s or "FAIL" in s or "OK" in s or "DIFF" in s or "reader" in s.lower():
                                self.output.info("CHECKLOG: " + s[:2000])
                except OSError:
                    pass
            raise ConanException(
                "upstream make check failed: " + json.dumps(marker)
            )

    def _install_generated_headers(self):
        """Copy configure-generated ndpi_define.h into the package.

        Upstream src/lib/Makefile.in installs only
        ``find $(top_srcdir)/src/include/*.h`` — i.e. the source tree,
        which holds ndpi_define.h.in but NOT the generated ndpi_define.h
        (AC_CONFIG_FILES src/include/ndpi_define.h lands in top_builddir).
        Without it any consumer including <ndpi/ndpi_api.h> fails with
        "fatal error: 'ndpi_define.h' file not found" (test_package).
        ndpi_config.h stays build-private (ndpi_main.h includes it only
        under NDPI_LIB_COMPILATION), so only ndpi_define.h is shipped.
        """
        dst_dir = os.path.join(self.package_folder, "include", "ndpi")
        dst = os.path.join(dst_dir, "ndpi_define.h")
        if os.path.isfile(dst):
            return
        candidates = [
            os.path.join(self.build_folder, "src", "include", "ndpi_define.h"),
            os.path.join(self.build_folder, "ndpi_define.h"),
            os.path.join(self.source_folder, "src", "include", "ndpi_define.h"),
            os.path.join(self.source_folder, "ndpi_define.h"),
        ]
        src = next((c for c in candidates if os.path.isfile(c)), None)
        if src is None:
            for root, _dirs, files in os.walk(self.build_folder):
                if "ndpi_define.h" in files:
                    src = os.path.join(root, "ndpi_define.h")
                    break
        if src is None:
            raise ConanException(
                "generated ndpi_define.h not found in build tree; "
                "cannot ship consumable headers"
            )
        os.makedirs(dst_dir, exist_ok=True)
        shutil.copyfile(src, dst)
        self.output.info("installed generated header from %s" % src)

    def package(self):
        shim_path = os.path.join(self.build_folder, "install-shim.sh")
        with open(shim_path, "w", encoding="utf-8") as f:
            f.write(_INSTALL_SHIM)
        cmd = (
            "make install DESTDIR=\"%s\" "
            "INSTALL=\"/bin/sh %s\" "
            "INSTALL_DATA='$(INSTALL)'"
        ) % (self.package_folder, shim_path)
        self.run(cmd, cwd=self.build_folder, env="conanbuild")

        # Drop libtool archives; keep shared/static libs per options.
        for root, _dirs, files in os.walk(self.package_folder):
            for name in files:
                if name.endswith(".la"):
                    os.remove(os.path.join(root, name))

        # Demo tools are build-time only (upstream tests use the build
        # tree). Ship a pure library package: lib + headers + pkgconfig.
        for sub in ("bin", "share"):
            path = os.path.join(self.package_folder, sub)
            if os.path.isdir(path):
                shutil.rmtree(path)

        # Upstream `make install` misses the generated ndpi_define.h
        # (see _install_generated_headers); stage it so consumers can
        # compile against <ndpi/ndpi_api.h>.
        self._install_generated_headers()

        # Persist upstream evidence for cache-hit re-emit via test_package.
        try:
            copy(
                self,
                "upstream_test_result.json",
                src=self.build_folder,
                dst=os.path.join(self.package_folder, "res"),
            )
            self.output.info("copied upstream_test_result.json to res/")
        except Exception as e:
            self.output.warning("copy upstream_test_result.json failed: %s" % e)

    def package_info(self):
        self.cpp_info.libs = ["ndpi"]
        self.cpp_info.set_property("cmake_file_name", "ndpi")
        self.cpp_info.set_property("cmake_target_name", "ndpi::ndpi")
        self.cpp_info.set_property("pkg_config_name", "libndpi")
