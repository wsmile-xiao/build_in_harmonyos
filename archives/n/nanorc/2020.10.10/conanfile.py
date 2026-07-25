#!/usr/bin/env python3
"""Conan recipe — nanorc 2020.10.10 (Improved Nano Syntax Highlighting Files).

Pure configuration file collection (.nanorc syntax highlighting files).
No compilation, no shared libraries, no executables.
Build system: custom (copy-only)
License: MIT
"""
from conan import ConanFile
from conan.tools.files import copy, get
import os


class NanorcConan(ConanFile):
    name = "nanorc"
    version = "2020.10.10"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"][self.version],
            destination=self.source_folder, strip_root=True)

    def build(self):
        pass

    def package(self):
        source_dir = self.source_folder
        copy(self, "*.nanorc", source_dir, os.path.join(self.package_folder, "share", "nanorc"))
        copy(self, "install.sh", source_dir, os.path.join(self.package_folder, "share", "nanorc"))
        copy(self, "nanorc", source_dir, os.path.join(self.package_folder, "share", "nanorc"))
        copy(self, "LICENSE", source_dir, os.path.join(self.package_folder, "licenses"))
        copy(self, "README.md", source_dir, os.path.join(self.package_folder, "share", "nanorc"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.runenv_info.define_path("NANORC_PATH", os.path.join(self.package_folder, "share", "nanorc"))
