#!/usr/bin/env python3
"""Conan recipe for awk (onetrueawk) 20251225 — Makefile build system.

awk (onetrueawk) is the classic AWK programming language implementation
maintained by Brian Kernighan. It is a command-line text processing tool.

Build: make CC=clang CFLAGS=-O2 -j1 (R9 parallel constraint).
Output: a.out binary, installed as bin/awk.

No dependencies. No patches needed.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AwkConan(ConanFile):
    name = "awk"
    version = "20251225"
    description = "The one true awk — AWK programming language interpreter"
    license = "MIT"
    homepage = "https://github.com/onetrueawk/awk"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf, NEVER from shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"

        # R9: Always use -j1, never -j$(nproc)
        # awk's Makefile: bison → maketab (HOSTCC) → proctab.c → compile → a.out
        # CC and HOSTCC both set to the same compiler (native build, no cross-compile)
        self.run(f"make CC={cc} HOSTCC={cc} CFLAGS=-O2 -j1")

        # Upstream test suite (make check → ./REGRESS) takes >2min on OHOS,
        # too slow for CI. Functional testing is done in test_package/ instead.

    def package(self):
        # Install binary (a.out → bin/awk) and man page
        copy(self, "a.out", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        # Rename a.out to awk
        bin_dir = os.path.join(self.package_folder, "bin")
        src_bin = os.path.join(bin_dir, "a.out")
        dst_bin = os.path.join(bin_dir, "awk")
        if os.path.isfile(src_bin):
            os.rename(src_bin, dst_bin)
            os.chmod(dst_bin, 0o755)
        # Copy man page
        copy(self, "awk.1", src=self.source_folder, dst=os.path.join(self.package_folder, "share/man/man1"), keep_path=False)

    def package_info(self):
        # Command-line tool: only bindirs, no libs
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
