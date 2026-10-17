#!/usr/bin/env python3
"""Conan recipe — logfault 0.8.5 (CMake header-only library).

logfault 是简单易用的跨平台 C++ header-only 日志库（CMake INTERFACE library）。
无任何第三方依赖，仅头文件分发。
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LogfaultConan(ConanFile):
    name = "logfault"
    version = "0.8.5"
    description = "Simple to use, header only C++ library for application-logging on all major platforms"
    license = "MIT"
    homepage = "https://github.com/jgaa/logfault"
    url = ""  # CI fills this
    topics = ("logging", "header-only", "cpp11", "cpp20")

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        cmake_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # HarmonyOS PC 目标需映射 CMAKE_SYSTEM_NAME（E017 同源做法）
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.variables["LOGFAULT_BUILD_TESTS"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "logfault")
        self.cpp_info.set_property("cmake_target_name", "logfault::logfault")
        self.cpp_info.libs = []