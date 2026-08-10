#!/usr/bin/env python3
"""Conan recipe for libcuckoo — header-only concurrent hash table library.

libcuckoo is an INTERFACE (header-only) C++ library. The CMake build system
is used only to install header files and CMake config files. No binary
library is produced. Based on Cuckoo hashing algorithm for high-performance
concurrent hash table operations.
"""
from conan import ConanFile
import os

from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibcuckooConan(ConanFile):
    name = "libcuckoo"
    version = "0.3.1"
    description = "High-performance concurrent hash table based on cuckoo hashing"
    license = "Apache-2.0"
    homepage = "https://github.com/efficient/libcuckoo"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "header-library"
    no_copy_source = True

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Fix CMake 4.x compatibility: upstream requires 3.1.0, but CMake >= 4.0
        # dropped support for < 3.5 even with CMAKE_POLICY_VERSION_MINIMUM in toolchain
        replace_in_file(
            self,
            os.path.join(self.source_folder, "CMakeLists.txt"),
            "cmake_minimum_required(VERSION 3.1.0)",
            "cmake_minimum_required(VERSION 3.5.0...3.31)",
        )
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.set_property("cmake_target_name", "libcuckoo::libcuckoo")
        self.cpp_info.system_libs = ["pthread"]
