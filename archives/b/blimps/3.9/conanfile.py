#!/usr/bin/env python3
"""Conan recipe for blimps 3.9.

BLIMPS (BLocks IMProved Searcher) is the FHCRC Blocks database searcher and
Block-Maker suite. Upstream 3.9 has no configure/CMake: two plain Makefiles
(blimps/Makefile.Linux, protomat/Makefile.Linux) build the command-line tools
plus the internal static library libblimps.a. The package ships the
executables (application) plus the docs/ runtime data tables (frequency,
scoring and codon-usage files that the tools load from the working
directory). libblimps.a is a build artifact and is not packaged.
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BlimpsConan(ConanFile):
    name = "blimps"
    version = "3.9"
    description = "FHCRC BLIMPS Blocks database improved searcher and Block Maker suite"
    license = "FHCRC non-commercial license"
    homepage = "https://ftp.ncbi.nlm.nih.gov/repository/blocks/unix/blimps/"
    url = "https://ftp.ncbi.nlm.nih.gov/repository/blocks/unix/blimps/"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler_tools(self):
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")
        toolchain_bin = os.path.dirname(cc)
        ar = compilers.get("ar") or (
            os.path.join(toolchain_bin, "llvm-ar") if toolchain_bin else "ar"
        )
        ranlib = compilers.get("ranlib") or (
            os.path.join(toolchain_bin, "llvm-ranlib") if toolchain_bin else "ranlib"
        )
        return cc, ar, ranlib

    def _sign_elf(self, path):
        if str(self.settings.os) != "OHOS" or not os.path.exists(path):
            return

        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.exists(sign_tool):
            os.chmod(path, 0o755)
            return

        signed = path + ".signed"
        if os.path.exists(objcopy):
            self.run(f'"{objcopy}" --remove-section .codesign "{path}" || true',
                     quiet=True)
        self.run(f'"{sign_tool}" sign -inFile "{path}" -outFile "{signed}" '
                 f"-selfSign 1", quiet=True)
        os.replace(signed, path)
        os.chmod(path, 0o755)

    def build(self):
        apply_conandata_patches(self)

        cc, ar, ranlib = self._compiler_tools()
        toolchain_bin = os.path.dirname(cc)
        if toolchain_bin:
            os.environ["PATH"] = toolchain_bin + os.pathsep + os.environ.get("PATH", "")

        # OHOS musl keeps a working gets symbol (ld-musl exports it); stdio.h
        # only hides the declaration behind a C11 version gate, so unpatched
        # gets(s) calls merely warn, link and run. The -D below is therefore
        # optional hardening, not a build requirement: it redirects all 129
        # gets(s) call sites to bounded fgets() with zero source changes --
        # an acknowledged semantic change (unbounded -> 8KB bounded read),
        # declared in notes.md and the package README. Drop the upstream
        # -ly: nothing in the tree references yacc library symbols and OHOS
        # ships no liby.
        # Defensive only: implicit declarations / int-conversion are measured
        # as warnings (not errors) on this clang 15 gnu17 toolchain; the
        # -Wno-error flags stay so a future -Werror-style switch cannot break
        # the build (upstream's XXWARN=-Werror is a dead variable today).
        optimiz = "-O2 -Wno-error=implicit-function-declaration -Wno-error=int-conversion"
        gets_def = "-D'gets(s)=fgets(s,8192,stdin)'"

        src = self.source_folder
        # -j1: the device make cannot create a jobserver fifo. `install`
        # builds everything and moves executables/libraries into the source
        # tree's bin/ and lib/ directories (upstream has no install prefix).
        self.run(
            f'make -j1 -f Makefile.Linux install CC="{cc}" AR="{ar}" '
            f'RANLIB="{ranlib}" OPTIMIZ="{optimiz}" DEFINES="{gets_def}" '
            f'LDLIBS="-lblimps -lm"',
            cwd=os.path.join(src, "blimps"),
        )
        # protomat/Makefile.Linux hardcodes CC=gcc plus a separate compile+
        # link driver CL=gcc, and bakes -c into CFLAGS; override all three.
        self.run(
            f'make -j1 -f Makefile.Linux install CC="{cc}" CL="{cc}" '
            f'CFLAGS="-O2 {gets_def} -c"',
            cwd=os.path.join(src, "protomat"),
        )

    def package(self):
        src = self.source_folder
        bin_dir = os.path.join(src, "bin")
        for name in sorted(os.listdir(bin_dir)):
            path = os.path.join(bin_dir, name)
            if os.path.isfile(path):
                copy(self, name, src=bin_dir,
                     dst=os.path.join(self.package_folder, "bin"))
                self._sign_elf(os.path.join(self.package_folder, "bin", name))

        copy(self, "LICENSE", src=src,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        # Runtime data tables the tools load from the working directory;
        # shipped under share/ so users can copy them next to their data.
        copy(self, "*", src=os.path.join(src, "docs"),
             dst=os.path.join(self.package_folder, "share", "blimps", "docs"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
