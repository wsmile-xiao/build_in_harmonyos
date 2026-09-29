#!/usr/bin/env python3
"""Conan test_package — functionalplus 0.2.26 消费者测试（header-only 交付形态）。

消费者面真实使用 fplus API（来自 conan 包 include/ 交付件）：
- include <fplus/fplus.hpp>，调用 keep_if/sum/join/transform/take/drop/replicate/
  sort_by/minimum/all 九组公共 API；
- 10 条运行期断言逐条打印读数，任一失败退出码非 0；
- 断言用显式检查而非 assert()（Release 下 NDEBUG 会把 assert 编译掉 → 假绿）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class FunctionalplusTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        # 把交付进包的 include/ 绝对路径传给 CMake，测试程序据此读取
        # package() 交付的 fplus.hpp 做内容指纹断言（§二.19 指向将安装的那一份）
        pkg_folder = self.dependencies["functionalplus"].package_folder
        cmake = CMake(self)
        cmake.configure(variables={
            "FPLUS_PKG_INCLUDE_DIR": os.path.join(pkg_folder, "include"),
        })
        cmake.build()

    def test(self):
        # L0d 门禁：此处必须真实执行被测二进制（拒绝空壳形态的测试方法）
        bindirs = self.cpp.build.bindirs
        if not bindirs:
            raise Exception("No bindirs found in test_package layout")
        bin_path = os.path.join(bindirs[0], "test_functionalplus")
        if not os.path.isfile(bin_path):
            raise Exception(f"Test binary not found: {bin_path}")
        self.run(bin_path, env="conanrun")
