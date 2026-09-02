#!/usr/bin/env python3
"""Conan recipe skeleton — gsl-lite 0.43.0 (header-only C++ GSL implementation).

gsl-lite 是 C++ Guideline Support Library 的轻量级、header-only 实现，
仅需安装头文件，无二进制编译。本文件为 bootstrap 阶段最小骨架，
adapt 阶段将依据实际 CMake 结构精调。
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class GslLiteConan(ConanFile):
    name = "gsl-lite"
    version = "0.43.0"
    description = "A single-file header-only version of Microsoft's Guidelines Support Library (GSL)"
    license = "MIT"
    homepage = "https://github.com/gsl-lite/gsl-lite"
    url = ""  # CI fills this

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        # R32: 平台判断必须 in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS", "FreeBSD", "Macos", "Windows"):
            raise ConanInvalidConfiguration(
                "gsl-lite 只支持 Linux/OHOS/FreeBSD/Macos/Windows，当前: {}".format(self.settings.os))

    def layout(self):
        cmake_layout(self)

    def package_id(self):
        # header-only 库，所有 settings 组合产出相同的包内容
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: CMake does not recognize OHOS as a target platform
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "gsl-lite")
        self.cpp_info.set_property("cmake_target_name", "gsl::gsl")
        self.cpp_info.libs = []
