#!/usr/bin/env python3
"""Conan recipe for protobuf-c 1.5.2 (CMake build system).

Builds the C runtime library (libprotobuf-c) using the build-cmake/ subdirectory.
protoc-gen-c (the code generator plugin) requires protobuf and is disabled
by default (BUILD_PROTOC=OFF). When protobuf is available, set build_protoc=True.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class ProtobufcConan(ConanFile):
    name = "protobuf-c"
    version = "1.5.2"
    description = "Protocol Buffers implementation in C"
    license = "BSD-2-Clause"
    homepage = "https://github.com/protobuf-c/protobuf-c"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "build_protoc": [True, False],
    }
    default_options = {
        "shared": False,
        "build_protoc": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        if self.options.build_protoc:
            self.requires("protobuf/33.6")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_PROTOC"] = self.options.build_protoc
        tc.variables["BUILD_TESTS"] = False
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(build_script_folder="build-cmake")
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["protobuf-c"]
        self.cpp_info.set_property("cmake_file_name", "protobuf-c")
        self.cpp_info.set_property("cmake_target_name", "protobuf-c::protobuf-c")
        self.cpp_info.set_property("pkg_config_name", "libprotobuf-c")
