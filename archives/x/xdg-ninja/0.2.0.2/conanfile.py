#!/usr/bin/env python3
"""Conan recipe for xdg-ninja 0.2.0.2 — Makefile-based shell script installer."""
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
import os


class XdgninjaConan(ConanFile):
    name = "xdg-ninja"
    version = "0.2.0.2"
    description = "A shell script which checks your HOME for unwanted files and directories"
    license = "MIT"
    homepage = "https://github.com/b3nj5m1n/xdg-ninja"
    url = ""

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

    def build(self):
        apply_conandata_patches(self)
        pass  # No compilation needed, shell script and data files

    def package(self):
        copy(self, "xdg-ninja.sh", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        import os as _os
        _os.rename(_os.path.join(self.package_folder, "bin", "xdg-ninja.sh"),
                   _os.path.join(self.package_folder, "bin", "xdg-ninja"))
        _os.chmod(_os.path.join(self.package_folder, "bin", "xdg-ninja"), 0o755)
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "doc", "xdg-ninja"))
        copy(self, "README.md", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "doc", "xdg-ninja"))
        copy(self, "man/xdg-ninja.1", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "programs/*", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "xdg-ninja", "programs"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []