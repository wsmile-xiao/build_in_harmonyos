#!/usr/bin/env python3
"""Conan recipe template — CMake projects.

Usage: Replace Edlib, edlib, 1.2.7, edlib 1.2.7, MIT, 
       Fill in requires() and cpp_info.libs as needed.

This template enforces R26: BUILD_SHARED_LIBS=OFF for system-name libraries.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class EdlibConan(ConanFile):
    name = "edlib"
    version = "1.2.7"
    description = "edlib 1.2.7"
    license = "MIT"
    homepage = "https://github.com/Martinsos/edlib"
    url = ""  # CI fills this

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
        # CMake 4.x 兼容：上游 cmake_minimum_required(3.2) 在 CMake 4.1.2 下失败
        # （CMake 4 移除了 <3.5 兼容），需注入策略版本下限（同 easyloggingpp 方案）
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # E092: CMake 不识别 OHOS，注入 Linux 平台 + armv8 处理器
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "armv8"
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
        self.cpp_info.libs = ["edlib"]
