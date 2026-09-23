#!/usr/bin/env python3
"""Conan recipe — chaiscript 6.1.0 (header-only).

Header-only embedded scripting language for C++. Requires C++14.
Zero external dependencies; stdlib is compiled into the consumer TU
via chaiscript.hpp (Std_Lib::library), no runtime dlopen needed.
"""
from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout
import os

required_conan_version = ">=2.0"


class ChaiscriptConan(ConanFile):
    name = "chaiscript"
    version = "6.1.0"
    package_type = "header-library"

    description = "Header-only embedded scripting language for C++ (zero dependencies, C++14)"
    homepage = "https://github.com/ChaiScript/ChaiScript"
    license = "BSD-2-Clause"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("scripting", "interpreter", "embedded", "header-only")

    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def layout(self):
        basic_layout(self, src_folder="src")

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def package(self):
        copy(self, "*.hpp",
             src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "chaiscript")
        self.cpp_info.set_property("cmake_target_name", "chaiscript::chaiscript")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
