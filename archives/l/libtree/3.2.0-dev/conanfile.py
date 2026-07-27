#!/usr/bin/env python3
"""Conan recipe for libtree — a tool that turns ldd into a tree."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibtreeConan(ConanFile):
    name = "libtree"
    version = "3.2.0-dev"
    description = "A tool that turns ldd into a tree and explains how shared libraries are found"
    license = "MIT"
    homepage = "https://github.com/haampie/libtree"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

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
        # CC is set by AutotoolsToolchain env, Makefile picks it up automatically
        self.run('make -j1 LDFLAGS=-static')

    def package(self):
        copy(self, "libtree", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "libtree.1", src=os.path.join(self.build_folder, "doc"),
             dst=os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
