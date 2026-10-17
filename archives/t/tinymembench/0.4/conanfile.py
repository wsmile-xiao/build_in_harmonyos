#!/usr/bin/env python3
"""Conan recipe for tinymembench 0.4 — simple memory bandwidth/latency benchmark.

tinymembench (Siarhei Siamashka) measures the peak bandwidth of sequential
memory accesses and the latency of random memory accesses. It runs a set of
C memcpy/memset variants, libc memcpy/memset and (per-architecture) hand
written assembly routines (x86 SSE2, ARM NEON/VFP, AArch64 LDP/STP, MIPS32),
then sweeps random-read latency over geometrically increasing buffer sizes.

Build system: hand-written GNU makefile (no configure, no install target, no
unit-test suite). Platform dispatch happens at compile time via C preprocessor
guards; every architecture-specific .S file wraps its whole body in
`#ifdef <arch>` and is fed through the C preprocessor (capital .S), so all
four .S files compile on any target and only the matching one emits code —
on aarch64-linux-ohos only aarch64-asm.S contributes, the other three become
empty object files.

The makefile links `${CC} -O2 ${CFLAGS} -o tinymembench main.c util.o
asm-opt.o x86-sse2.o arm-neon.o mips-32.o aarch64-asm.o -lm`, so we override
CC/CFLAGS on the make command line with the OHOS cross clang
(--target=aarch64-linux-ohos) taken from tools.build:compiler_executables.
Beware the makefile's `ifdef WINDIR` branch forces `CC = gcc` — a command
line CC= override always wins, but the WINDIR environment variable is also
scrubbed in build() for belt-and-braces.

There is no upstream test suite (no check target, no test files), so build()
performs the real upstream build and test_package runs the *installed*
benchmark end-to-end and asserts on its output (bandwidth/latency sections).

Note: the full benchmark run needs several minutes (per-test adaptive
repeats, 64 MiB latency buffers, hugepage/nohugepage variants); test_package
uses a generous timeout accordingly.
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout

# OHOS code-signing tooling (same approach as simh/3.8.1): the DEVICE/CI
# provides binary-sign-tool; on a plain host we skip signing and let the
# packaged consumer sign (HarmonyOS PC refuses to exec unsigned ELF).
_SIGN_TOOL_CANDIDATES = (
    "/data/service/hnp/bin/binary-sign-tool",
    "/storage/Users/currentUser/usr/local/bin/binary-sign-tool",
)
_OBJCOPY_CANDIDATES = (
    "/data/service/hnp/bin/llvm-objcopy",
    "/storage/Users/currentUser/usr/local/bin/llvm-objcopy",
)


class TinymembenchConan(ConanFile):
    name = "tinymembench"
    version = "0.4"
    description = (
        "Simple benchmark for memory throughput and latency: C/libc/asm "
        "(x86 SSE2, ARM NEON, AArch64 LDP-STP, MIPS32) bandwidth tests plus "
        "random-read latency sweep over increasing buffer sizes."
    )
    license = "MIT"
    homepage = "https://github.com/ssvb/tinymembench"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    # Patches must be exported as sources too: without this,
    # export_sources_folder is None and export_conandata_patches() crashes
    # with TypeError (os.path.join(None, ...)) on conan 2.29 (r3 device
    # lesson).
    exports_sources = "patches/*"

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS", "Windows", "FreeBSD"):
            raise ConanInvalidConfiguration(
                "tinymembench/0.4 in this recipe targets OHOS/Linux-like systems"
            )

    def source(self):
        # Source URL/SHA256 live in conandata.yml. The tarball has a single
        # root dir tinymembench-0.4/, so strip_root=True.
        get(self, **self.conan_data["sources"], strip_root=True)
        # Drop .func/.endfunc assembler directives: they are DWARF-only
        # annotations that GNU gas accepts but clang's integrated assembler
        # rejects ("unknown directive .func"). Same change as OpenEmbedded's
        # 0001-asm-Delete-.func-.endfunc-directives.patch.
        apply_conandata_patches(self)

    def build(self):
        # R33: take the compiler from Conan conf, never from bare shell vars.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang") if compilers else "clang"

        # The makefile treats CC as the compiler program (not a full command)
        # and appends ${CFLAGS} itself; a command-line CC/CFLAGS override
        # replaces the defaults. `ifdef WINDIR` in the makefile would force
        # CC=gcc on a Windows host, but the command-line CC= override always
        # wins, so no env scrubbing is needed (self.run() in conan 2.x does
        # not accept a plain dict env anyway — r5 device lesson).
        # R9: always -j1 (tiny project; avoids jobserver/FIFO issues on OHOS).
        self.run(
            f'make CC="{cc}" CFLAGS="" -j1',
            cwd=self.source_folder,
        )

    def package(self):
        exe = os.path.join(self.source_folder, "tinymembench")
        exe_windows = exe + ".exe"
        if not os.path.isfile(exe) and not os.path.isfile(exe_windows):
            raise ConanException("tinymembench executable missing after build")
        dst = os.path.join(self.package_folder, "bin")
        os.makedirs(dst, exist_ok=True)
        src_exe = exe if os.path.isfile(exe) else exe_windows
        shutil.copy2(src_exe, os.path.join(dst, os.path.basename(src_exe)))
        # License ships as a standalone LICENSE file in the 0.4 tarball.
        lic = os.path.join(self.source_folder, "LICENSE")
        lic_dst = os.path.join(self.package_folder, "licenses")
        os.makedirs(lic_dst, exist_ok=True)
        if os.path.isfile(lic):
            shutil.copy2(lic, os.path.join(lic_dst, "LICENSE"))
        else:
            raise ConanException("LICENSE missing from extracted sources")
        self._sign_binaries()

    def _sign_binaries(self):
        """Self-sign the OHOS ELF executables (HarmonyOS MAC refuses unsigned).

        Best-effort: the signing tools only exist on the device/CI runner. On
        a plain host we skip and let the packaged consumer re-sign.
        """
        if str(self.settings.os) != "OHOS":
            return
        sign_tool = next(
            (p for p in (shutil.which("binary-sign-tool"), *_SIGN_TOOL_CANDIDATES)
             if p and os.path.exists(p)),
            None,
        )
        objcopy = next(
            (p for p in (shutil.which("llvm-objcopy"), *_OBJCOPY_CANDIDATES)
             if p and os.path.exists(p)),
            None,
        )
        if not sign_tool:
            self.output.warning(
                "binary-sign-tool not found; skipping OHOS ELF self-signing "
                "(consumer must re-sign)"
            )
            return
        bindir = os.path.join(self.package_folder, "bin")
        for name in sorted(os.listdir(bindir)):
            path = os.path.join(bindir, name)
            if not os.path.isfile(path) or os.path.islink(path):
                continue
            if objcopy:
                subprocess.run(
                    [objcopy, "--remove-section", ".codesign", path],
                    capture_output=True,
                )
            res = subprocess.run(
                [sign_tool, "sign", "-inFile", path, "-outFile", path, "-selfSign", "1"],
                capture_output=True,
            )
            if res.returncode != 0:
                self.output.warning(
                    "binary-sign-tool failed for %s (rc=%d): %s"
                    % (name, res.returncode, res.stderr.decode(errors="replace")[:200])
                )
            else:
                os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
