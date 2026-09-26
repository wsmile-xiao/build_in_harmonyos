#!/usr/bin/env python3
"""Conan recipe — confu_json 1.2.4 (header-only C++20 library).

confu_json is a header-only (INTERFACE) C++20 library: it serializes /
deserializes arbitrary boost::fusion-adapted types to/from JSON. The package
installs the 5 public headers to include/confu_json; there is no compiled
artifact, so cpp_info exposes no libs. Requires magic_enum + boost (headers).
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class ConfujsonConan(ConanFile):
    name = "confu_json"
    version = "1.2.4"
    description = "confu_json 1.2.4 — C++20 JSON (de)serialization for boost::fusion-adapted types"
    license = "BSL-1.0"
    homepage = "https://github.com/werto87/confu_json"
    url = "https://github.com/werto87/confu_json"

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Runtime/header dependencies of the public headers
        self.requires("magic_enum/0.9.7")
        self.requires("boost/1.90.0")
        # NOTE: catch2 is only used by the upstream test suite, not by the
        # package itself; it is not a package requirement.

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.variables["BUILD_TESTS"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # header-only: nothing to link, nothing in libdirs/bindirs
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "confu_json")
        self.cpp_info.set_property("cmake_target_name", "confu_json::confu_json")
