#!/usr/bin/env python3
"""Conan recipe for plutosvg. Platform task version 1.3.3; upstream tag is v0.0.8."""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class PlutosvgConan(ConanFile):
    name = "plutosvg"
    version = "1.3.3"
    description = "Tiny SVG rendering library in C"
    license = "MIT"
    homepage = "https://github.com/sammycage/plutosvg"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("plutovg/1.3.3")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["PLUTOSVG_ENABLE_FREETYPE"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["plutosvg"]
        self.cpp_info.includedirs = ["include/plutosvg", "include"]
        self.cpp_info.requires = ["plutovg::plutovg"]
        self.cpp_info.set_property("cmake_file_name", "plutosvg")
        self.cpp_info.set_property("cmake_target_name", "plutosvg::plutosvg")
