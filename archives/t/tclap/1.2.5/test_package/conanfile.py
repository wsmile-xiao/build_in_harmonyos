#!/usr/bin/env python3
"""Conan test_package — tclap 1.2.5 消费者测试（header-only 交付形态）。

消费者面真实使用 tclap：
- `#include <tclap/CmdLine.h>`（来自 conan 包 include/tclap/ 交付件）；
- 构造 CmdLine 解析参数：ValueArg / SwitchArg / MultiArg / int 转换 / 缺必填异常；
- 交付面指纹：头文件数 25、CmdLine.h 字节数 14764、上游 include guard/版权行、无 lib/、
  licenses/COPYING 已交付（§二.19：头文件包必须断言「打包的就是那一份」）；
- 11 条运行期断言逐条打印读数，任一失败退出码非 0。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class TclapTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # L0d 门禁：必须真实执行被测二进制（拒绝 echo/print/true 形态的空壳）
        bindirs = self.cpp.build.bindirs
        if not bindirs:
            raise Exception("No bindirs found in test_package layout")
        bin_path = os.path.join(bindirs[0], "test_tclap")
        if not os.path.isfile(bin_path):
            raise Exception(f"Test binary not found: {bin_path}")
        pkg_folder = self.dependencies["tclap"].package_folder
        if not pkg_folder or not os.path.isdir(pkg_folder):
            raise Exception(f"Package folder not found: {pkg_folder}")
        # 把**实际交付的包目录**交给消费者测试做交付面断言
        self.run(f'"{bin_path}" "{pkg_folder}"', env="conanrun")
