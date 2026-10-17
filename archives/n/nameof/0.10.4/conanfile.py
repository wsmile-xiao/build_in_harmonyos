#!/usr/bin/env python3
"""Conan recipe for nameof 0.10.4 — header-only C++17 library for names of types/variables/enums."""
import os

from conan import ConanFile
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class NameofConan(ConanFile):
    name = "nameof"
    version = "0.10.4"
    description = "Nameof C++17 library for getting name of variable, type, enum, member, function."
    license = "MIT"
    homepage = "https://github.com/Neargye/nameof"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = "nameof", "reflection", "header-only"
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        copy(self, "LICENSE*", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "nameof.hpp", os.path.join(self.source_folder, "include"),
             os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "nameof")
        self.cpp_info.set_property("cmake_target_name", "nameof::nameof")
        self.cpp_info.set_property("pkg_config_name", "nameof")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
