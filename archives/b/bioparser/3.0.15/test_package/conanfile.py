#!/usr/bin/env python3
"""Conan test_package — bioparser 3.0.15 消费者验证.

仅使用已安装包的公开头文件与公开 API（Parser::Create/Parse），
模拟上层业务组件消费 bioparser；验证编译、链接、调用与可观察结果。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class BioparserTestConan(ConanFile):
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
        # 直接运行消费者二进制（带测试 FASTA 数据），不依赖 ctest 无参注册
        self.run(
            f"{os.path.join(self.cpp.build.bindirs[0], 'test_bioparser')} "
            f"{os.path.join(self.source_folder, 'sample.fasta')}",
            env="conanrun")