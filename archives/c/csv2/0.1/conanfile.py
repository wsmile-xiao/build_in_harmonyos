#!/usr/bin/env python3
"""Conan recipe — csv2 0.1 (CMake header-only CSV reader/writer library).

csv2 是 header-only 的 C++ CSV 解析库（Reader/Writer，模板参数配置分隔符/
引号/首行表头/trim 策略），CMake INTERFACE library，无任何第三方依赖。
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Csv2Conan(ConanFile):
    name = "csv2"
    version = "0.1"
    description = "Fast, header-only C++ library for parsing/writing CSV data"
    license = "MIT"
    homepage = "https://github.com/p-ranav/csv2"
    url = ""  # CI fills this
    topics = ("csv", "parser", "header-only", "cpp11")

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
        # R32: OS 判断必须同时覆盖 Linux 与 OHOS
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.variables["CSV2_TEST"] = False  # 上游测试不进配方，避免把 doctest 带入制品
        tc.variables["CSV2_SAMPLES"] = False
        tc.variables["CSV2_DEMO"] = False
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
        self.cpp_info.set_property("cmake_file_name", "csv2")
        self.cpp_info.set_property("cmake_target_name", "csv2::csv2")
        self.cpp_info.libs = []