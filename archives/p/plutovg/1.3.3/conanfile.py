#!/usr/bin/env python3
"""Conan recipe for the PlutoVG 1.3.3 C library."""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class PlutovgConan(ConanFile):
    name = "plutovg"
    version = "1.3.3"
    description = "Standalone 2D vector graphics library written in C"
    license = "MIT"
    homepage = "https://github.com/sammycage/plutovg"
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
        # R26: System-name libraries default to static
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Build the upstream rendering example as an end-to-end smoke test.
        tc.variables["PLUTOVG_BUILD_EXAMPLES"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])
        self.run(os.path.join("examples", "smiley"), cwd=self.build_folder)

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["plutovg"]
        self.cpp_info.includedirs = ["include/plutovg", "include"]
        self.cpp_info.system_libs = ["m", "pthread"]
        self.cpp_info.set_property("cmake_file_name", "plutovg")
        self.cpp_info.set_property("cmake_target_name", "plutovg::plutovg")
        self.cpp_info.set_property("pkg_config_name", "plutovg")
