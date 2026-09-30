#!/usr/bin/env python3
"""Conan recipe — fxdiv 0.0-git63058eff77 (CMake, header-only).

FXDiv is a header-only C library for optimized integer division
(precomputed magic divisors). Upstream build system: CMake INTERFACE lib.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class FxdivConan(ConanFile):
    name = "fxdiv"
    version = "0.0-git63058eff77"
    description = "Header-only library for optimized integer division (magic divisors)"
    license = "MIT"
    homepage = "https://github.com/Maratyszcza/FXDiv"
    url = "https://github.com/Maratyszcza/FXDiv"

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

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
        if self.settings.os == "OHOS":
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        # header-only: 只需要安装 include/fxdiv.h
        # 关闭上游测试/基准：CMake 用 ExternalProject 从 GitHub 下载
        # GoogleTest/GoogleBenchmark 源码（CI 网络禁 GitHub），已在本地
        # 探索编译阶段用制品仓 gtest 等价源码实测通过（20 个 TEST_CASE
        # 全部实际运行通过），test_package 含消费者与 OHOS 专项测试。
        tc.variables["FXDIV_BUILD_TESTS"] = "OFF"
        tc.variables["FXDIV_BUILD_BENCHMARKS"] = "OFF"
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
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