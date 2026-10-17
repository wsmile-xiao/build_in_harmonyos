#!/usr/bin/env python3
"""Conan test_package — iowow 1.4.18 消费者验证（Conan L1 official test）。

CI 通过 `conan create` 自动运行本测试。验证内容为 iwkv 持久化键值数据库
全生命周期真实行为（创建/写入/读取/更新/删除/游标/重开持久化），
R34：调用被测包真实公开 API 并验证可观察结果，非空壳打印。

File location: archives/i/iowow/1.4.18/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class IowowTestConan(ConanFile):
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
        # 真实运行测试二进制（R34：非空壳）——exit code 非 0 即失败
        cmake = CMake(self)
        cmake.test()
        self.run(
            f"{os.path.join(self.cpp.build.bindirs[0], 'test_iowow')}",
            env="conanrun",
        )
