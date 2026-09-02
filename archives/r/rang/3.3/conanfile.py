#!/usr/bin/env python3
"""Conan recipe for rang 3.3 — header-only terminal color/format library.

Downstream expects:
  find_package(rang REQUIRED)
  target_link_libraries(... PRIVATE rang::rang)
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class RangConan(ConanFile):
    name = "rang"
    version = "3.3"
    description = "A Minimal, Header only Modern c++ library for colors in your terminal"
    license = "Unlicense"
    homepage = "https://github.com/agauniyal/rang"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = "terminal", "color", "header-only"
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
        # Header-only: no build step required; apply any conandata patches.
        apply_conandata_patches(self)

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "*.hpp", os.path.join(self.source_folder, "include"),
             os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "rang")
        self.cpp_info.set_property("cmake_target_name", "rang::rang")
        self.cpp_info.set_property("pkg_config_name", "rang")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []