#!/usr/bin/env python3
"""Conan recipe — lavat (terminal lava lamp simulation).

lavat is a command-line tool that simulates a lava lamp in the terminal
using metaballs and termbox2. It produces a single binary, no libraries.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class LavatConan(ConanFile):
    name = "lavat"
    version = "3.0.0"
    description = "Lava lamp simulation using metaballs in the terminal"
    license = "MIT"
    homepage = "https://github.com/AngelJumbo/lavat"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf, never from shell env vars.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang")

        # Use -j1 to avoid parallel build issues on low-resource CI
        self.run(f"make CC={cc} -j1")

    def package(self):
        # lavat is a single binary tool — copy to bin/
        copy(self, "lavat", self.build_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # Application package — binary is in bin/
        self.cpp_info.bindirs = ["bin"]
