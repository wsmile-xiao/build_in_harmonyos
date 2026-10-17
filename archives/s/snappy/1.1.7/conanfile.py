#!/usr/bin/env python3
"""Conan recipe for snappy 1.1.7 — fast compression/decompression library.

Snappy is a fast data compression/decompression library developed by Google.
It aims for high speed rather than maximum compression ratio.

Build system: CMake
Library output: libsnappy (static by default)
No external dependencies.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class SnappyConan(ConanFile):
    name = "snappy"
    version = "1.1.7"
    description = "Fast compression/decompression library by Google"
    license = "BSD-3-Clause"
    homepage = "https://github.com/google/snappy"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "with_tests": [True, False]}
    default_options = {"shared": False, "with_tests": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 仅在 with_tests=True 时引入 GoogleTest（剥离测试：默认不依赖 googletest，
        # 保持 libsnappy 干净；googletest/1.12.1 为仓库已 conan 适配版本）。
        if self.options.with_tests:
            self.requires("googletest/1.12.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # OHOS hmmac blocks /bin/sh; make hardcodes SHELL=/bin/sh (E346).
        # Use Ninja generator (execs compiler directly) to bypass the shell.
        self.conf.define("tools.cmake.cmaketoolchain:generator", "Ninja")
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # 剥离测试：默认 SNAPPY_BUILD_TESTS=OFF（主包干净，无 googletest 依赖）；
        # 仅 with_tests=True 时编译并运行上游测试 snappy_unittest。
        if self.options.with_tests:
            tc.variables["SNAPPY_BUILD_TESTS"] = True
            # snappy 1.1.7 用 find_package(GTest) 的旧式 GTEST_INCLUDE_DIRS 变量
            # （CMakeDeps config 模式不设置该变量），此处显式注入 googletest 头文件路径。
            gtest = self.dependencies.get("googletest")
            if gtest:
                incs = gtest.cpp_info.includedirs
                if incs:
                    tc.variables["GTEST_INCLUDE_DIRS"] = ";".join(incs)
        else:
            tc.variables["SNAPPY_BUILD_TESTS"] = False
        tc.variables["SNAPPY_BUILD_BENCHMARKS"] = False
        # CMake >=3.5 removed compatibility with cmake_minimum_required <3.5;
        # snappy 1.1.7 declares VERSION 3.1. Pass via -D (cache_variables) so
        # it is honored on the configure command line.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["CMAKE_MAKE_PROGRAM"] = "/data/service/hnp/bin/ninja"
        tc.generate()
        if self.options.with_tests:
            # 生成 googletest 的 CMake config（GTest::gtest 等 target）
            cd = CMakeDeps(self)
            cd.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["snappy"]
