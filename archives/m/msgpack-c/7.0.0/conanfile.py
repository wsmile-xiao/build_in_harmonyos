#!/usr/bin/env python3
"""Conan recipe for msgpack-c 7.0.0 — MessagePack serialization library for C.

CMake-based C library with no external dependencies.
Builds both shared and static libraries.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class MsgpackcConan(ConanFile):
    name = "msgpack-c"
    version = "7.0.0"
    description = "MessagePack is an efficient binary serialization format for C/C++"
    license = "Boost Software License 1.0"
    homepage = "https://msgpack.org/"
    url = "https://github.com/msgpack/msgpack-c"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

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
        tc.cache_variables["MSGPACK_BUILD_TESTS"] = False
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
        self.cpp_info.libs = ["msgpack-c"]
        self.cpp_info.set_property("cmake_file_name", "msgpack-c")
        self.cpp_info.set_property("cmake_target_name", "msgpack-c::msgpack-c")
        self.cpp_info.set_property("pkg_config_name", "msgpack-c")
