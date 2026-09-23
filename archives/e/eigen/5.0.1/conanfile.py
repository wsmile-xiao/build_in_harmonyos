#!/usr/bin/env python3
"""Conan recipe for Eigen 5.0.1, a header-only linear algebra library."""

import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


required_conan_version = ">=2.0"


class EigenConan(ConanFile):
    name = "eigen"
    version = "5.0.1"
    package_type = "header-library"

    description = "C++ template library for linear algebra (header-only)"
    homepage = "https://eigen.tuxfamily.org/"
    license = "MPL-2.0"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self, src_folder="src")

    def validate(self):
        check_min_cppstd(self, "14")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["EIGEN_BUILD_BLAS"] = "OFF"
        tc.variables["EIGEN_BUILD_LAPACK"] = "OFF"
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["EIGEN_BUILD_DOC"] = "OFF"
        tc.variables["EIGEN_BUILD_DEMOS"] = "OFF"
        tc.variables["EIGEN_BUILD_PKGCONFIG"] = "ON"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "COPYING*",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Eigen3")
        self.cpp_info.set_property("cmake_target_name", "Eigen3::Eigen")
        self.cpp_info.includedirs = ["include/eigen3"]
