#!/usr/bin/env python3
"""Conan recipe for gapp 1.0.1 — a C++ genetic algorithms library."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class GappConan(ConanFile):
    name = "gapp"
    version = "1.0.1"
    description = "A genetic algorithms library in C++ for single- and multi-objective optimization"
    license = "MIT"
    homepage = "https://github.com/KRM7/gapp"
    url = "https://github.com/KRM7/gapp"
    topics = ("genetic-algorithm", "multi-objective-optimization", "optimization", "cpp20")
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
        # The upstream test/benchmark/example trees are not part of the packaged
        # library build: they need Catch2 (a test-only dependency) and are run
        # separately on the device, see notes.md.
        tc.variables["GAPP_BUILD_TESTS"] = "OFF"
        tc.variables["GAPP_BUILD_BENCHMARKS"] = "OFF"
        tc.variables["GAPP_BUILD_EXAMPLES"] = "OFF"
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "gapp")
        self.cpp_info.set_property("cmake_target_name", "gapp::gapp")
        self.cpp_info.libs = ["gapp"]
        # Upstream installs to "${CMAKE_INSTALL_LIBDIR}/$<CONFIG>"
        # (see CMakeLists.txt install(TARGETS ...)), i.e. lib/<build_type>/.
        self.cpp_info.libdirs = [os.path.join("lib", str(self.settings.build_type))]
