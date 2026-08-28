#!/usr/bin/env python3
"""Conan recipe — protozero 1.8.2 (CMake, header-only).

protozero is a minimalistic protocol buffer (protobuf) decoder/encoder
written in C++. It is header-only: upstream CMake `install()` only installs
the `include/protozero` headers (no compiled library). Upstream also builds a
Catch2-based test suite (reader_tests, unit_tests) and a `pbf-decoder` CLI
tool; writer tests additionally require protobuf (not a runtime dependency of
this package). The package ships headers only, so no libs are produced.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class ProtozeroConan(ConanFile):
    name = "protozero"
    version = "1.8.2"
    description = "Minimalistic protocol buffer decoder and encoder in C++ (header-only)"
    license = "BSD-2-Clause"
    homepage = "https://github.com/mapbox/protozero"
    url = "https://github.com/mapbox/protozero"
    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Header-only package: disable upstream test/build targets so the
        # package build stays self-contained (no protobuf needed).
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Header-only: no libs. Expose the include dir + required C++ standard.
        self.cpp_info.set_property("cmake_file_name", "protozero")
        self.cpp_info.set_property("cmake_target_name", "protozero::protozero")
        self.cpp_info.requires = []
        self.cpp_info.cxxflags = []
