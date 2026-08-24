#!/usr/bin/env python3
"""Conan test_package — ccp 1.0.0 消费者测试。

E298: 消费者链接包内共享库（libccp.so，SONAME=libccp.so）时，CTest/裸执行
不加载 conanrun 运行环境，动态加载器无法定位库。test() 中显式把包 lib 目录
注入 LD_LIBRARY_PATH 再运行消费者二进制（VirtualRunEnv 为空时兜底，双保险）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CcpTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # 显式运行消费者二进制；先注入包 lib 目录到 LD_LIBRARY_PATH
        # （libccp.so 带 SONAME，运行时按 SONAME 解析）
        pkg = self.dependencies["ccp"]
        lib_dir = os.path.join(pkg.package_folder, "lib")
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_ccp")
        self.run(f'LD_LIBRARY_PATH="{lib_dir}" "{test_bin}"', env="conanrun")
