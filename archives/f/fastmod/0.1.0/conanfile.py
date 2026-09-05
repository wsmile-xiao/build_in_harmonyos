#!/usr/bin/env python3
"""Conan recipe for fastmod 0.1.0, a header-only C/C++ library."""
import os

from conan import ConanFile
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class FastmodConan(ConanFile):
    name = "fastmod"
    version = "0.1.0"
    description = "C/C++ header-only library for fast 32-bit division and remainder operations on 64-bit hardware"
    license = "Apache-2.0"
    homepage = "https://github.com/lemire/fastmod"
    url = "https://github.com/lemire/fastmod"

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

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
        # Keep the upstream default CTest inventory: two benchmark targets.
        tc.variables["FASTMOD_EXHAUSTIVE_TESTS"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # The upstream CMake test suite registers moddivnbenchmark and
        # modnbenchmark. Run it explicitly so the Conan log records ctest.
        self.run("ctest --output-on-failure", cwd=self.build_folder)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "fastmod")
        self.cpp_info.set_property("cmake_target_name", "fastmod::fastmod")
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
