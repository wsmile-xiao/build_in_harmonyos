#!/usr/bin/env python3
"""Conan recipe for clipmenu - clipboard management using dmenu."""
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
import os


class ClipmenuConan(ConanFile):
    name = "clipmenu"
    version = "6.2.0"
    description = "Clipboard management using dmenu"
    license = "Public Domain"
    homepage = "https://github.com/cdown/clipmenu"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Runtime dependencies
        self.requires("xsel/1.2.1")
        self.requires("clipnotify/1.0.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # No build step - pure shell scripts
        pass

    def package(self):
        # Install shell scripts
        for script in ["clipmenu", "clipmenud", "clipdel", "clipctl", "clipfsck"]:
            copy(self, script,
                 src=self.source_folder,
                 dst=os.path.join(self.package_folder, "bin"),
                 keep_path=False)
        # Ship the upstream test suite so test_package can run it.
        # The upstream test resolves the main script via "$location/../clipmenu",
        # so also copy the main script to the package root to keep that layout.
        copy(self, "tests/*",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "tests"),
             keep_path=False)
        copy(self, "clipmenu",
             src=self.source_folder,
             dst=self.package_folder,
             keep_path=False)
        # Install license
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        # No libraries, just scripts
        self.cpp_info.libs = []
