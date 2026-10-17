#!/usr/bin/env python3
"""Conan recipe for dbg-macro 0.5.1.1 (header-only, upstream 0.5.1).

The upstream Catch2 submodule is restored from the pinned archive before the
upstream CMake/CTest suite is built and executed.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class DbgMacroConan(ConanFile):
    name = "dbg-macro"
    version = "0.5.1.1"
    package_type = "header-library"

    description = "dbg(...) macro for printf-style debugging (header-only)"
    homepage = "https://github.com/sharkdp/dbg-macro"
    license = "MIT"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"

    no_copy_source = True

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        get(
            self,
            **self.conan_data["test_sources"]["catch2"],
            strip_root=True,
            destination=os.path.join(self.source_folder, "tests", "Catch2"),
        )

    def package_id(self):
        self.info.clear()

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["DBG_MACRO_ENABLE_TESTS"] = True
        tc.variables["BUILD_TESTING"] = True
        tc.variables["CMAKE_CXX_STANDARD"] = "17"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = True
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        cmake.ctest(cli_args=["--output-on-failure"])

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "dbg_macro")
        self.cpp_info.set_property("cmake_target_name", "dbg_macro::dbg_macro")
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
