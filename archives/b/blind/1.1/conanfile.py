#!/usr/bin/env python3
"""Conan recipe — blind 1.1 (makefile)

blind is a collection of command line video manipulation utilities from suckless.org.
Build system: simple Makefile (no configure script).
License: ISC
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class BlindConan(ConanFile):
    name = "blind"
    version = "1.1"
    description = "Collection of command line video manipulation utilities for Unix"
    license = "ISC"
    homepage = "https://tools.suckless.org/blind/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # AutotoolsToolchain sets CC in the build environment
        # Make picks up CC from environment (Makefile's config.mk doesn't set CC)
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        for f in os.listdir(self.source_folder):
            if f.startswith("blind-") and "." not in f:
                copy(self, f, self.source_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
