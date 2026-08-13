#!/usr/bin/env python3
"""Conan recipe — eigen 3.4.1 (header-only).

Eigen: C++ template library for linear algebra (matrices, vectors,
numerical solvers). Header-only, zero dependencies.
"""
from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.layout import basic_layout
import os

required_conan_version = ">=2.0"


class EigenConan(ConanFile):
    name = "eigen"
    version = "3.4.1"
    package_type = "header-library"

    description = "C++ template library for linear algebra (header-only)"
    homepage = "https://eigen.tuxfamily.org/"
    license = "MPL-2.0"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"

    exports_sources = "patches/*"

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["EIGEN_BUILD_BLAS"] = "OFF"
        tc.variables["EIGEN_BUILD_LAPACK"] = "OFF"
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["EIGEN_BUILD_DOC"] = "OFF"
        tc.variables["EIGEN_BUILD_PKGCONFIG"] = "ON"
        tc.generate()

    def build(self):
        # header-only：仅 CMake 配置验证头文件结构完整（不编译库）
        cmake = CMake(self)
        cmake.configure()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Eigen3")
        self.cpp_info.set_property("cmake_target_name", "Eigen3::Eigen")
        self.cpp_info.includedirs = ["include/eigen3"]