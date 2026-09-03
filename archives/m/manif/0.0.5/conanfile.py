#!/usr/bin/env python3
"""Conan recipe — manif 0.0.5 (header-only Lie group C++ library).

manif 是 header-only（CMake INTERFACE library）的李群/流形库，提供
SO(2)/SO(3)/SE(2)/SE(3)/SE_2_3/SGal(3)/R^n 等群操作的模板实现，
依赖 Eigen3 头文件库。本配方在 OHOS/Linux 上仅需安装头文件与 CMake 包配置。
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class ManifConan(ConanFile):
    name = "manif"
    version = "0.0.5"
    description = "A small C++11 header-only library for Lie theory (SO2/SO3/SE2/SE3/SE_2_3/SGal3/Rn)"
    license = "MIT"
    homepage = "https://github.com/artivis/manif"
    url = "https://github.com/artivis/manif"
    topics = ("lie-group", "manifold", "slam", "robotics", "header-only")

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    requires = "eigen/3.4.0"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # 上游默认关闭测试/示例/benchmark，保持最小构建
        tc.variables["BUILD_TESTING"] = False
        tc.variables["BUILD_EXAMPLES"] = False
        tc.variables["BUILD_BENCHMARKING"] = False
        tc.variables["BUILD_PYTHON_BINDINGS"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "manif")
        self.cpp_info.set_property("cmake_target_name", "MANIF::manif")
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
