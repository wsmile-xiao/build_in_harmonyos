#!/usr/bin/env python3
"""Conan recipe for bitsery 5.2.5, a header-only C++ serialization library."""
import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.files import copy, get


class BitseryConan(ConanFile):
    name = "bitsery"
    version = "5.2.5"
    description = "Header-only binary serialization library for C++"
    license = "MIT"
    homepage = "https://github.com/fraillt/bitsery"
    url = ""

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        if self.settings.compiler.cppstd:
            check_min_cppstd(self, "11")

    def package_id(self):
        self.info.clear()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "bitsery/*", src=os.path.join(self.source_folder, "include"), dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.set_property("cmake_file_name", "Bitsery")
        self.cpp_info.set_property("cmake_target_name", "Bitsery::bitsery")
