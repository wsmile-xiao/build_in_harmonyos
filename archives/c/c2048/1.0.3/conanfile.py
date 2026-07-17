#!/usr/bin/env python3
"""Conan recipe — c2048 1.0.3

c2048 is a small C99 console 2048 game built by a simple upstream Makefile.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class C2048Conan(ConanFile):
    name = "c2048"
    version = "1.0.3"
    description = "Console version of the game 2048 implemented in C"
    license = "MIT"
    homepage = "https://github.com/mevdschee/2048.c"
    url = "https://github.com/mevdschee/2048.c"

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

    def _make_args(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c") or "clang"
        return f'CC="{cc}"'

    def build(self):
        apply_conandata_patches(self)
        make_args = self._make_args()
        self.run(f"make {make_args}", cwd=self.source_folder)
        if can_run(self):
            self.run(f"make {make_args} test", cwd=self.source_folder)

    def package(self):
        self.run(f'make {self._make_args()} install PREFIX="{self.package_folder}"', cwd=self.source_folder)
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
