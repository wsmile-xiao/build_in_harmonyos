#!/usr/bin/env python3
"""Conan recipe for pasco 20040505 - Windows IE index.dat forensic parser (raw Makefile).

ODESSA/pasco ships only `src/Makefile` (no configure / CMake / Meson) and hardcodes the
compiler as the literal `gcc`, with no $(CC)/$(CFLAGS)/$(LDFLAGS) references anywhere.
Measured on the official 4032-byte tarball (sha256 a3b8ee7be9..), 10-line Makefile:
    grep -c 'override' = 0 ; grep -c '$(CC)' = 0 ; grep -c '$(CFLAGS)' = 0
Because the compile line contains no variable at all, `make CC=clang` on the command
line cannot reach it -- a two-line source patch is mandatory to introduce $(CC).
The patch is a pure in-place edit (10 -> 10 lines, lines 4 and 7 only); pasco.c is
byte-identical to upstream (sha256 9ffa61f8..).

Produces the `pasco` executable. Adapted for HarmonyOS OHOS (aarch64).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PascoConan(ConanFile):
    name = "pasco"
    version = "20040505"
    description = "Forensic parser that dumps Windows Internet Explorer index.dat cache/store records as delimited text"
    license = "BSD-3-Clause"
    homepage = "https://sourceforge.net/projects/odessa/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Pure C parser: only libc/libm, which upstream already names with -lm -lc.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        # Archive root is pasco_20040505_1/, sources live in src/ underneath it.
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: the compiler comes from the Conan conf, never from bare shell env vars.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = (compilers or {}).get("c", "clang")
        cflags = "-O2" if str(self.settings.build_type) == "Release" else ""
        # R9: -j1. Upstream `all` just calls `install`, which builds src/pasco and
        # copies it to ../bin; the patch adds the `mkdir -p ../bin` the tarball lacks.
        self.run(f"make -C src install -j1 CC={cc} CFLAGS={cflags}", cwd=self.source_folder)

    def package(self):
        copy(self, "pasco", os.path.join(self.source_folder, "src"),
             os.path.join(self.package_folder, "bin"))
        docdir = os.path.join(self.package_folder, "doc", "pasco")
        copy(self, "Readme.txt", self.source_folder, docdir)
        copy(self, "CHANGES", self.source_folder, docdir)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
