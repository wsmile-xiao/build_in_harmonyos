#!/usr/bin/env python3
"""Conan recipe for properties-cpp - A C++11 property/signal library (header-only).

properties-cpp is a simple, header-only C++11 library for properties and signals.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.scm import Version
import os


class PropertiescppConan(ConanFile):
    name = "properties-cpp"
    version = "0.0.4"
    description = "A simple convenience library for handling properties and signals in C++11"
    license = "LGPL-3.0"
    homepage = "https://gitlab.com/ubports/development/core/lib-cpp/properties-cpp"
    url = ""

    package_type = "header-library"  # Header-only library

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # Header-only, no dependencies

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTING"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Copy license
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_id(self):
        # Header-only library, no package_id needed
        self.info.clear()

    def package_info(self):
        # Header-only library
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        
        # Include directories
        self.cpp_info.includedirs = ["include"]
        
        # pkg-config name
        self.cpp_info.set_property("pkg_config_name", "properties-cpp")
        
        # Requires C++11 or later
        if Version(self.settings.compiler.cppstd) < "11":
            self.cpp_info.cxxflags = ["-std=c++11"]
