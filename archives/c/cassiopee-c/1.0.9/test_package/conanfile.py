#!/usr/bin/env python3
"""Conan test_package — cassiopee-c 1.0.9 消费者验证。

test() 通过 CMake 构建真实消费者二进制（consumer_test.cxx），仅链接库的
公开头文件与 API（CassieIndexer 构建索引 + CassieSearch 搜索 + 索引序列化
保存/恢复），运行并断言退出码为 0（R34/PF3：非 print-only 空壳测试）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CassiopeecTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Cassiopee.h 公开头直接包含 boost 头文件（boost/archive/*.hpp），
        # 消费者编译必须可见 boost include；boost 作为传递依赖时 CMakeDeps
        # 不导出 include 目录，故 test_package 显式声明（adql 同款先例）
        self.requires("boost/1.90.0.4.1")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        # 兜底：即使 ctest 未注册也直接运行消费者二进制
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_cassiopee-c"), env="conanrun")