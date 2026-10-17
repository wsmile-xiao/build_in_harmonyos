#!/usr/bin/env python3
"""Conan recipe — sophus 1.22.10 (header-only C++ Lie groups, CMake, requires Eigen3)"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class SophusConan(ConanFile):
    name = "sophus"
    version = "1.22.10"
    description = "C++ implementation of Lie groups using Eigen (SO(2), SO(3), SE(2), SE(3), Sim(2), Sim(3), RxSO(2), RxSO(3))"
    license = "MIT"
    homepage = "https://github.com/strasdat/Sophus"

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("eigen/3.4.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["SOPHUS_INSTALL"] = "ON"
        tc.variables["BUILD_SOPHUS_TESTS"] = "OFF"
        tc.variables["BUILD_SOPHUS_EXAMPLES"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = []
        # 上游在无 fmt 时自动开启 basic logging（common.hpp 走 SOPHUS_USE_BASIC_LOGGING 分支，不依赖 fmt 头文件）
        self.cpp_info.defines = ["SOPHUS_USE_BASIC_LOGGING=1"]
        self.cpp_info.set_property("cmake_file_name", "Sophus")
        self.cpp_info.set_property("cmake_target_name", "Sophus::Sophus")
