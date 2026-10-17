#!/usr/bin/env python3
"""Conan recipe for yyjson 0.13.0 — High-performance JSON library in ANSI C."""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class YyjsonConan(ConanFile):
    name = "yyjson"
    version = "0.13.0"
    description = "High-performance JSON library written in ANSI C"
    license = "MIT"
    homepage = "https://github.com/ibireme/yyjson"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(
            self,
            filename="yyjson-0.13.0.tar.gz",
            strip_root=True,
            **self.conan_data["sources"],
        )

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["YYJSON_BUILD_TESTS"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["yyjson"]
        self.cpp_info.set_property("cmake_file_name", "yyjson")
        self.cpp_info.set_property("cmake_target_name", "yyjson::yyjson")
        self.cpp_info.set_property("pkg_config_name", "yyjson")