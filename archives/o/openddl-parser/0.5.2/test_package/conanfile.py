#!/usr/bin/env python3
"""Conan test_package — openddl-parser 0.5.2 消费者验证.

消费者仅通过库已安装/导出的公开头文件 (openddlparser/OpenDDLParser.h) 与
公开 API（OpenDDLParser::parse / getRoot / DDLNode 遍历 / getVersion）编译、
链接并运行，验证第三方使用者可以正常消费本库。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class OpenddlParserTestConan(ConanFile):
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
        cmake = CMake(self)
        cmake.build()
        # 真实消费者运行：直接执行链接被测包静态库的测试二进制（R34/L0d）
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_openddl_parser")
        self.run(bin_path, env="conanrun")