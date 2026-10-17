#!/usr/bin/env python3
"""Conan recipe — nng 1.8.0 (CMake), HarmonyOS PC 适配."""

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class NngConan(ConanFile):
    name = "nng"
    version = "1.8.0"
    description = "nng (nanomsg-next-generation) 轻量级消息库，支持多种通信协议与传输方式"
    license = "MIT"
    homepage = "https://nng.nanomsg.org/"
    url = "https://github.com/nanomsg/nng"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["NNG_TESTS"] = "OFF"
        tc.variables["NNG_TOOLS"] = "ON"
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
        self.cpp_info.libs = ["nng"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "nng")
        self.cpp_info.set_property("cmake_target_name", "nng::nng")