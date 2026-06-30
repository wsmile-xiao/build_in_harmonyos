#!/usr/bin/env python3
"""Conan recipe — atinout 0.9.1

atinout is a simple C program that reads AT commands from input,
sends them to a modem device, and outputs the responses.

Build system: simple Makefile (no configure script).
License: GPL-3.0
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain


class AtinoutConan(ConanFile):
    name = "atinout"
    version = "0.9.1"
    description = "AT commands as input are sent to modem and responses given as output"
    license = "GPL-3.0"
    homepage = "https://atinout.sourceforge.net/"
    url = ""  # CI fills this

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
        # atinout uses a simple Makefile with CC and PREFIX variables
        # R26: atinout is a standalone tool, only depends on libc, no system lib collision risk
        tc.generate()

    def build(self):
        # atinout has no configure script, just a simple Makefile
        # Pass CC from Conan environment to override Makefile's CC=gcc,
        # but keep Makefile's CFLAGS (which includes -DVERSION="0.9.1")
        apply_conandata_patches(self)
        self.run('make -j1 CC="${CC}"')

    def package(self):
        # Install binary and man page to the package
        copy(self, "atinout", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "atinout.1", src=self.build_folder, dst=os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        # atinout is a command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
