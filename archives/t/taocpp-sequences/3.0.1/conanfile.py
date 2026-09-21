#!/usr/bin/env python3
"""Conan recipe for taocpp-sequences 3.0.1 (CMake, header-only)."""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class TaocppSequencesConan(ConanFile):
    name = "taocpp-sequences"
    version = "3.0.1"
    description = "C++11 header-only library providing compile-time sequences and algorithms"
    license = "MIT"
    homepage = "https://github.com/taocpp/sequences"
    url = "https://github.com/taocpp/sequences"

    package_type = "header-library"

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
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["TAOCPP_SEQUENCES_BUILD_TESTS"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5",
                                   "TAOCPP_SEQUENCES_BUILD_TESTS": "ON"})
        cmake.build()
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "taocpp-sequences")
        self.cpp_info.set_property("cmake_target_name", "taocpp::sequences")
        self.cpp_info.includedirs = ["include"]
