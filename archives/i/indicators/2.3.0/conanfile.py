#!/usr/bin/env python3
"""Conan recipe — indicators 2.3.0 (CMake header-only library).

indicators 是 p-ranav/indicators 的 header-only 活动指示器库（进度条/旋转器/活动指示）。
header-only（CMake INTERFACE 风格安装：include/indicators + cmake config + pkgconfig），
无第三方编译期依赖（内部携带 termcolor 单头）。上游自带 Conan 1.x 配方，按 Conan 2.x 重写。
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class IndicatorsConan(ConanFile):
    name = "indicators"
    version = "2.3.0"
    description = "Activity Indicators for Modern C++ - thread-safe progress bars, spinners and activity indicators (header-only)"
    license = "MIT"
    homepage = "https://github.com/p-ranav/indicators"
    url = ""  # CI fills this
    topics = ("indicators", "progress", "spinner", "activity-indicator", "header-only", "cpp11")

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        cmake_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "indicators")
        self.cpp_info.set_property("cmake_target_name", "indicators::indicators")
        self.cpp_info.libs = []