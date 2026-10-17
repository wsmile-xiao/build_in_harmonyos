#!/usr/bin/env python3
"""Conan recipe — ascii 3.32

Interactive ASCII reference tool — query character names, decimal,
octal, hexadecimal and binary codes.

Build system: plain Makefile (no configure script).
The 'ascii' make target auto-generates splashscreen.h and nametable.h
as prerequisites, so a single 'make ascii' builds the binary.
License: BSD-2-Clause
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain


class AsciiConan(ConanFile):
    name = "ascii"
    version = "3.32"
    description = "Interactive ASCII reference — query character names, decimal, octal, hexadecimal and binary codes"
    license = "BSD-2-Clause"
    homepage = "https://gitlab.com/esr/ascii"
    url = ""

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        self.folders.build = "."
        self.folders.generators = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Build the ascii binary.
        # The Makefile generates splashscreen.h and nametable.h as
        # prerequisites of the 'ascii' target.
        # R33: Get compiler from Conan conf, not undefined shell variables
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        self.run(f'make ascii -j1 CC="{cc}"')

    def package(self):
        # Install binary to bin/
        copy(self, "ascii", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))
        # Install man page if available (asciidoctor may not be on OHOS)
        copy(self, "ascii.1", src=self.build_folder, dst=os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        # ascii is a command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
