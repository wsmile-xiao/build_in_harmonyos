#!/usr/bin/env python3
"""Conan recipe — aixlog 1.5.0 (header-only).

Header-only C++11 logging library. Zero dependencies.
"""
from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout
import os

required_conan_version = ">=2.0"


class AixlogConan(ConanFile):
    name = "aixlog"
    version = "1.5.0"
    package_type = "header-library"

    description = "Header-only C++11 logging library (zero dependencies)"
    homepage = "https://github.com/badaix/aixlog"
    license = "MIT"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"

    exports_sources = "patches/*"

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def package(self):
        copy(self, "include/aixlog.hpp", src=self.source_folder, dst=self.package_folder)
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "aixlog")
        self.cpp_info.set_property("cmake_target_name", "aixlog::aixlog")
        self.cpp_info.includedirs = ["include"]