#!/usr/bin/env python3
"""Conan recipe for fortune-mod 9708 — Makefile-based command-line tool.

fortune-mod is the infamous electronic fortune-cookie generator.
Build system: plain Makefile (no configure script).

Adaptations for OHOS:
  - POSIX regex instead of BSD regex (R3)
  - Offensive content disabled (rot.c EOF issue on OHOS)
  - DESTDIR support added to Makefile and datfiles/Makefile
  - PREFIX variable for relocatable installation
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class FortuneConan(ConanFile):
    name = "fortune"
    version = "9708"
    description = "Infamous electronic fortune-cookie generator"
    license = "BSD-4-Clause"
    homepage = "https://www.ibiblio.org/pub/linux/games/amusements/fortune/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: Get compiler from Conan conf, not shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={})
        cc = compilers.get("c", "clang") if compilers else "clang"
        # Build with PREFIX pointing to package folder so FORTDIR is correct
        # R9: Use -j1 (not -j$(nproc))
        self.run(f"make CC={cc} PREFIX={self.package_folder} -j1", cwd=self.source_folder)

    def package(self):
        # Install to package folder using PREFIX + DESTDIR
        # PREFIX sets the install layout, DESTDIR="" means install directly under PREFIX
        self.run(f"make PREFIX={self.package_folder} DESTDIR= install", cwd=self.source_folder)

    def package_info(self):
        # fortune binary is in games/, strfile/unstr in bin/
        self.cpp_info.bindirs = ["games", "bin"]
        # Fortune data files (cookies + .dat)
        self.cpp_info.resdirs = ["share/games/fortunes"]
