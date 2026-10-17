#!/usr/bin/env python3
"""Conan 2 recipe for Nuklear 4.12.8."""

import os

from conan import ConanFile
from conan.tools.files import copy, get


class NuklearConan(ConanFile):
    name = "nuklear"
    version = "4.12.8"
    description = "Single-header ANSI C immediate-mode GUI library"
    license = "MIT OR Unlicense"
    homepage = "https://github.com/Immediate-Mode-UI/Nuklear"
    url = "https://github.com/Immediate-Mode-UI/Nuklear"
    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def package(self):
        copy(
            self,
            "nuklear.h",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        copy(
            self,
            "Readme.md",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "res"),
        )

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        if str(self.settings.os) != "Windows":
            self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("cmake_file_name", "nuklear")
        self.cpp_info.set_property("cmake_target_name", "nuklear::nuklear")
        self.cpp_info.set_property("pkg_config_name", "nuklear")
