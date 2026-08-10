#!/usr/bin/env python3
"""Conan recipe for msgpack-cxx 7.0.0 — header-only C++ MessagePack library."""

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class MsgpackcxxConan(ConanFile):
    name = "msgpack-cxx"
    version = "7.0.0"
    description = "MessagePack is an efficient binary serialization format for C++"
    license = "BSL-1.0"
    homepage = "https://github.com/msgpack/msgpack-c"

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
        tc.variables["MSGPACK_USE_BOOST"] = "OFF"
        tc.variables["MSGPACK_BUILD_EXAMPLES"] = "OFF"
        tc.variables["MSGPACK_BUILD_TESTS"] = "OFF"
        tc.variables["MSGPACK_BUILD_DOCS"] = "OFF"
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
        self.cpp_info.libs = []
        self.cpp_info.defines = ["MSGPACK_NO_BOOST"]
        self.cpp_info.set_property("cmake_target_name", "msgpack-cxx::msgpack-cxx")
