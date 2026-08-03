#!/usr/bin/env python3
"""Conan recipe — wraplinux 1.7 (autotools, host-side boot wrapper tool).

 wraplinux packages an x86 Linux kernel + initrd into ELF/NBI. Its reloc/ and
 highmove/ boot stubs are x86 16/32-bit assembly linked via OUTPUT_ARCH(i386);
 they cannot be produced by the arm64 clang toolchain and have no meaning on
 HarmonyOS PC (arm64). The adaptation builds the host-side pure-C tool by
 stubbing the embedded x86 binaries with empty files, so wraplinux still links
 and runs as a host packaging utility (the x86 relocation stubs are omitted).
"""
import os
import re

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


# MCONFIG.in hardcodes the x86 cross-toolchain as literal strings (autoconf
# never probes them — no @VAR@ substitution): `CC_FOR_TARGET = gcc -m32`,
# `LD_FOR_TARGET = ld -m elf_i386`, `OBJCOPY_FOR_TARGET = objcopy`,
# `CFLAGS_FOR_TARGET = -W -Wall -I. -g -Os -march=i386 -mregparm=3 -fPIE
# -ffreestanding`, `LDFLAGS_FOR_TARGET =`. On arm64 clang, `-march=i386` is
# rejected (`unsupported argument 'i386' to option '-march='`) and arm64 ld
# rejects `-m elf_i386` (`unrecognised emulation mode`). configure copies these
# verbatim into MCONFIG; `make` can also re-run `./configure` via the
# `MCONFIG: configure MCONFIG.in config.h.in` rule, regenerating MCONFIG from
# the (un-patched) MCONFIG.in. Patch MCONFIG.in at the source so EVERY configure
# run emits neutralised values, and also patch the generated MCONFIG after
# configure runs (belt-and-suspenders). Idempotent.
_ARM64_TARGET_OVERRIDES = {
    "CC_FOR_TARGET": "$(CC)",          # host CC, no -m32
    "CFLAGS_FOR_TARGET": "",           # drop -march=i386 -mregparm=3 -fPIE -ffreestanding
    "LDFLAGS_FOR_TARGET": "",
    "LD_FOR_TARGET": "/bin/true",      # i386 link rule -> no-op
    "OBJCOPY_FOR_TARGET": "/bin/true", # i386 objcopy rule -> no-op
}


class WrapLinuxConan(ConanFile):
    name = "wraplinux"
    version = "1.7"
    description = "Utility to wrap an x86 Linux kernel and initrd into an ELF or NBI file"
    license = "GPL-2.0"
    homepage = "https://cdn.kernel.org/pub/linux/utils/boot/wraplinux"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # E002/E206: HarmonyOS /tmp is erofs (read-only) and HMDFS setgid makes
        # `umask 077 && mktemp -d` dirs unwritable to the current uid. Point
        # TMPDIR/TMP/TEMP at a writable build subdir so autotools' `${TMPDIR:-/tmp}`
        # template succeeds and the `./confXXXX` fallback (patched below) is not
        # the only path. Conan runs build() with this env inherited.
        tmpdir = os.path.join(self.build_folder, "hmbs-tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir
        tc = AutotoolsToolchain(self)
        tc.generate()

    def _patch_autotools_mktemp_hmdfs(self, path):
        """HMDFS workaround for autotools 2.69 tmp-dir creation (E002/E206).

        configure and config.status create a temp dir with
            `(umask 077 && mktemp -d "./confXXXXXX")`
        On HMDFS the new dir inherits the parent owner uid via setgid, so when
        the current uid differs the 0700 permission mask (from umask 077) makes
        it unwritable — subsequent `subs1.awk` / `defines.awk` writes hit
        `Permission denied`. Combined with erofs read-only /tmp the fallback
        chain fully breaks config.status (`could not setup config files
        machinery`). Switch umask 077 -> umask 000 so group/other write bits
        let non-owner uids write helper scripts inside the temp dir. Idempotent.
        """
        if not path or not os.path.isfile(path):
            return
        with open(path, "r", encoding="utf-8", errors="surrogateescape") as f:
            txt = f.read()
        new = txt.replace("umask 077 && mktemp -d", "umask 000 && mktemp -d")
        new = new.replace("umask 077 && mkdir \"$tmp\"", "umask 000 && mkdir \"$tmp\"")
        if new != txt:
            with open(path, "w", encoding="utf-8", errors="surrogateescape") as f:
                f.write(new)

    def _apply_target_overrides(self, path):
        """Rewrite the x86 *_FOR_TARGET assignments in MCONFIG / MCONFIG.in.

        Each assignment is `KEY<ws>=<ws>value` and the value may span
        multiple makefile lines joined by a trailing backslash (the upstream
        `CFLAGS_FOR_TARGET = ... -march=i386 ... \\` `  -fPIE -ffreestanding`
        does exactly this). We walk the file line-by-line, and when we meet a
        `KEY=` line we replace the whole assignment (first line + any
        `\\`-continuation lines) with a single `KEY\t\t= value` line.

        Idempotent: a line already equal to the new value is left alone.
        """
        if not path or not os.path.isfile(path):
            return
        with open(path, "r", encoding="utf-8", errors="surrogateescape") as f:
            lines = f.readlines()
        out = []
        i = 0
        changed = False
        keys = set(_ARM64_TARGET_OVERRIDES)
        while i < len(lines):
            line = lines[i]
            stripped = line.lstrip()
            mname = None
            for k in keys:
                if stripped.startswith(k) and re.match(
                    re.escape(k) + r"\s*=", stripped
                ):
                    mname = k
                    break
            if mname is None:
                out.append(line)
                i += 1
                continue
            # Consume the first line plus any following `\\`-continuation lines.
            j = i
            while j < len(lines) and (
                j == i or lines[j - 1].rstrip().endswith("\\")
            ):
                j += 1
            val = _ARM64_TARGET_OVERRIDES[mname]
            new_line = "{}\t\t= {}\n".format(mname, val)
            if "".join(lines[i:j]) != new_line:
                out.append(new_line)
                changed = True
            else:
                out.extend(lines[i:j])
            i = j
        if changed:
            with open(path, "w", encoding="utf-8", errors="surrogateescape") as f:
                f.writelines(out)

    def build(self):
        apply_conandata_patches(self)
        # version.h is normally generated by the Debian build; synthesize it.
        with open(os.path.join(self.source_folder, "version.h"), "w", encoding="utf-8") as f:
            f.write('#define WRAPLINUX_VERSION "1.7"\n')
        # E002/E206: pre-patch upstream configure before running it — on HMDFS
        # its `umask 077 && mktemp -d` template creates a temp dir we cannot
        # write into (setgid uid mismatch), breaking the whole configure run.
        self._patch_autotools_mktemp_hmdfs(os.path.join(self.source_folder, "configure"))
        # Conan 2.30 arch setting has no "arm64" literal (valid arm64-family
        # values are armv8/armv8.3/armv8_32/aarch64/arm64ec). Comparing
        # self.settings.arch == "arm64" makes Conan validate the RHS literal
        # and raise ConanException('Invalid setting'). str() the value first
        # and test membership in the real arm64 family, matching blake3/diamond.
        arch = str(self.settings.arch)
        is_arm64 = arch in ("armv8", "armv8.3", "armv8_32", "aarch64", "arm64ec")
        is_arm64 = is_arm64 and str(self.settings.os) in ("Linux", "OHOS")
        sf = self.source_folder
        if is_arm64:
            # Patch MCONFIG.in BEFORE configure so the cross-toolchain literals
            # (`gcc -m32`, `-march=i386`, `ld -m elf_i386`, `objcopy`) are
            # neutralised at the source. Every `./configure` invocation —
            # including ones `make` re-triggers via
            # `MCONFIG: configure MCONFIG.in config.h.in` — then emits an
            # arm64-safe MCONFIG. Without this, `make` regenerates MCONFIG from
            # the pristine MCONFIG.in and re-introduces `-march=i386` /
            # `ld -m elf_i386`, which arm64 clang/ld reject.
            self._apply_target_overrides(os.path.join(sf, "MCONFIG.in"))
        autotools = Autotools(self)
        autotools.configure()
        # config.status is generated by configure with the same umask 077 mktemp
        # template — patch it too so re-invocations (make rule deps) survive.
        self._patch_autotools_mktemp_hmdfs(os.path.join(self.build_folder, "config.status"))
        if is_arm64:
            # Also patch the generated MCONFIG in case configure already ran
            # before the MCONFIG.in patch, or `make` re-runs configure later.
            # The MCONFIG.in patch above is the durable fix; this is the
            # immediate post-configure sweep.
            for mcfg in (
                os.path.join(self.build_folder, "MCONFIG"),
                os.path.join(sf, "MCONFIG"),
            ):
                self._apply_target_overrides(mcfg)
            # Stub the x86 artifacts so Makefile rules that reference them
            # (reloc.o needs reloc/reloc.bin; reloc/reloc.bin needs reloc.elf;
            # reloc/reloc.elf needs reloc/*.o) find targets present and do not
            # invoke the i386 toolchain (CC_FOR_TARGET / LD_FOR_TARGET /
            # OBJCOPY_FOR_TARGET are undefined for arm64).
            for p in ("reloc/reloc.elf", "reloc/reloc.bin",
                      "highmove/highmove.elf", "highmove/highmove.bin"):
                open(os.path.join(sf, p), "wb").close()
            # Pre-create empty stub .o files for every x86 boot object the
            # Makefile knows about (reloc/*.o, highmove/*.o). These feed only
            # the (already-stubbed) reloc.elf/highmove.elf rules, never the host
            # tool; stubbing them cuts make's timestamp-chain at the leaf so
            # it never invokes CC_FOR_TARGET on reloc_linux.c / a20.S / etc.
            # (those contain x86 inline asm and .code16 directives that the
            # arm64 clang backend cannot assemble, even with the MCONFIG
            # override above).
            for sub in ("reloc", "highmove"):
                d = os.path.join(sf, sub)
                if not os.path.isdir(d):
                    continue
                for fn in os.listdir(d):
                    if fn.endswith((".c", ".S")):
                        open(os.path.join(d, fn[:-2] + ".o"), "wb").close()
            # Assemble the host-visible wrappers reloc.S/highmove.S with the
            # host CC (they are .incbin wrappers, not x86 asm); .incbin embeds
            # the empty .bin as a zero-length segment, producing reloc.o /
            # highmove.o. The x86 reloc/*.S/highmove/*.S are never compiled.
            self.run("make reloc.o highmove.o -j1", cwd=sf)
        # wraplinux ships a hand-written `Makefile` (not Makefile.in +
        # automake) living in the *source* folder; `configure` (run above by
        # autotools.configure() in the source folder) writes `MCONFIG` next
        # to that Makefile, which `-include MCONFIG` then picks up. Conan's
        # `autotools.make()` runs `make` in the *build* folder, where neither
        # Makefile nor MCONFIG exists (`make: *** No targets specified and no
        # makefile found`). Run `make` in the source folder instead, where the
        # upstream Makefile + generated MCONFIG live.
        self.run("make -j1", cwd=sf)

        # ── 上游官方测试 (L1) ──────────────────────────────────────────────
        # wraplinux 1.7 上游 Makefile (hand-written, 非 automake) genuinely 无
        # check/test 目标——已显式审计确认 (test_package/MANIFEST.yml 的
        # upstream_tests_exist: false + 结构化 upstream_test_audit, 逐文件枚举
        # 上游 43 文件并裁定每个为非测试入口)。故 build() 不集成 `make check`
        # (upstream_test_in_build: false)：对无 check 目标的 Makefile 跑 make check
        # 只会得 exit 2 `No rule to make target 'check'. Stop.`，无意义且 Conan
        # self.run() 会把它当 ConanException 终止 build()。
        #
        # 上游测试证据 (HMBS_UPSTREAM_TEST_RESULT) 由 test_package/test.sh 在
        # test 阶段产生——对齐已通过 hmbs 门禁的 osmctools/0.9 与 sipcalc/1.1.6
        # 范例写法 (upstream_test_in_build: false 路径)：test.sh 在 smoke 断言结
        # 束后 echo no_tests 标记, reason 嵌入审计结论与 make check 输出指纹。本
        # build() 不重复跑 make check，避免 build 阶段多余退出非 0 风险。

    def package(self):
        # `make` runs in the *source* folder (see build()) — the upstream hand-written
        # Makefile + generated MCONFIG live there, so the linked `wraplinux` binary
        # is produced in self.source_folder, NOT self.build_folder. Copying from
        # build_folder shipped an empty bin/ and the test_package then hit
        # `inaccessible or not found` (exit 127) on the absolute path. Same source
        # folder holds wraplinux.1 (the man page).
        copy(self, "wraplinux", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "wraplinux.1", self.source_folder, os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
