#!/usr/bin/env python3
"""Conan recipe — pacvim 1.1.1

PacVim is an ncurses-based game that teaches Vim commands.
Build system: raw Makefile (no configure script), C++ project.
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class PacvimConan(ConanFile):
    name = "pacvim"
    version = "1.1.1"
    description = "PacVim — an ncurses-based game that teaches Vim commands"
    license = "MIT"
    homepage = "https://github.com/jmoon018/PacVim"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("ncurses/6.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _make_args(self) -> str:
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = compilers.get("cpp") or "clang++"
        ncurses = self.dependencies["ncurses"]
        ncurses_inc = os.path.join(ncurses.package_folder, "include")
        ncurses_lib = os.path.join(ncurses.package_folder, "lib")
        return (
            f'CXX="{cxx}" '
            f'EXTRA_INC="{ncurses_inc}" '
            f'EXTRA_LIB="{ncurses_lib}" '
            f'PREFIX="{self.package_folder}"'
        )

    def build(self):
        apply_conandata_patches(self)
        self.run(f"make {self._make_args()} -j1", cwd=self.source_folder)

    def package(self):
        self.run(f'make {self._make_args()} install', cwd=self.source_folder)
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.resdirs = ["share"]
