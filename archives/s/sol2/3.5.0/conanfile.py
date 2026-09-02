#!/usr/bin/env python3
"""Conan recipe for sol2 3.5.0, a header-only Lua C++ binding."""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class Sol2Conan(ConanFile):
    name = "sol2"
    version = "3.5.0"
    description = "C++ bindings to Lua, packaged as a header-only library."
    license = "MIT"
    homepage = "https://github.com/ThePhD/sol2"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("lua", "bindings", "header-only")
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        self.output.info("sol2 is header-only; no native library is built")

    def package(self):
        copy(self, "*", os.path.join(self.source_folder, "include"),
             os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE.txt", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "sol2")
        self.cpp_info.set_property("cmake_target_name", "sol2::sol2")
