#!/usr/bin/env python3
"""Conan recipe — aa3d 1.0

ASCII art stereogram generator (ASCII-3D-2000 tech demo from AA-Project).
Converts a simple text-file 3D depth map into a random-dot ASCII stereogram.

Build system: plain Makefile (implicit rule `aa3d: aa3d.c`), no configure.
License: GPL-2.0-or-later (derived from XaoS, see header of aa3d.c)
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import GnuToolchain
from conan.tools.layout import basic_layout


class Aa3dConan(ConanFile):
    name = "aa3d"
    version = "1.0"
    description = "ASCII art stereogram generator — convert a text 3D depth map to a random-dot ASCII stereogram"
    license = "GPL-2.0-or-later"
    homepage = "http://aa-project.sourceforge.net/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = GnuToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # R33: get compiler from Conan conf (never bare shell env vars)
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        # R9: always -j1 for old single-file make projects
        self.run(f'make -j1 CC="{cc}"', cwd=self.source_folder)

    def package(self):
        # aa3d is a command-line tool: install the binary to bin/
        copy(self, "aa3d", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # Command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
