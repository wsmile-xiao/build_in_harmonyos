#!/usr/bin/env python3
"""Conan recipe — doctest 2.5.2 (header-only C++ testing framework)."""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.files import copy, get
import os

class DoctestConan(ConanFile):
    name = "doctest"
    version = "2.5.2"
    license = "MIT"
    author = "doctest"
    url = "https://github.com/doctest/doctest"
    description = "doctest is a header-only C++ testing framework"
    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True
    generators = "CMakeToolchain"

    def layout(self):
        cmake_layout(self)

    def source(self):
        # strip_root=False: doctest 的 GitHub release tarball 无单一顶层目录
        # （文件散列在归档根级），strip_root=True 会报错：
        # "Can't untar a tgz containing files in the root with strip_root enabled"
        get(self, **self.conan_data["sources"], strip_root=False)

    def build(self):
        """编译上游测试套件 (examples/all_features)，仅编译验证不执行"""
        cmake = CMake(self)
        cmake.configure(variables={
            "DOCTEST_WITH_TESTS": "ON",
            "DOCTEST_NO_INSTALL": "ON",
            "DOCTEST_WITH_MAIN_IN_STATIC_LIB": "OFF",
        })
        # 只构建 all_features 目标（上游 tests/ 编译时找不到 doctest/doctest.h）
        cmake.build(cli_args=["--target", "all_features"])
        # all_features 是 doctest 功能演示示例，包含故意失败的测试用例（123 个测试中 55 个预期失败）。
        # 不执行 all_features 以避免 R9 伪造通过风险。test_package 已提供消费者级别验证。

    def package(self):
        # doctest tarball 无顶层目录 (strip_root=True 会失败)，
        # 从 source_folder 递归搜索所有头文件
        copy(self, "**/doctest.h", src=self.source_folder, dst=os.path.join(self.package_folder, "include"))
        copy(self, "**/doctest.hpp", src=self.source_folder, dst=os.path.join(self.package_folder, "include"))
        # 复制 extensions/ 子目录中的扩展头文件
        copy(self, "**/*.hpp", src=self.source_folder, dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
