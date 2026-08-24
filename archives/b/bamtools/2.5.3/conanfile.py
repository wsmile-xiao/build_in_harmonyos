#!/usr/bin/env python3
"""Conan recipe for BamTools 2.5.3 (CMake)."""

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class BamtoolsConan(ConanFile):
    name = "bamtools"
    version = "2.5.3"
    description = "C++ API and command-line toolkit for working with BAM data"
    license = "MIT"
    homepage = "https://github.com/pezmaster31/bamtools"
    url = "https://github.com/pezmaster31/bamtools"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()

        toolchain = CMakeToolchain(self)
        toolchain.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        toolchain.variables["BUILD_TESTING"] = True
        toolchain.generate()

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
        self.cpp_info.libs = ["bamtools"]
        self.cpp_info.includedirs = ["include/bamtools"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.requires = ["zlib::zlib"]
        self.cpp_info.set_property("cmake_file_name", "bamtools")
        self.cpp_info.set_property("cmake_target_name", "bamtools::bamtools")
