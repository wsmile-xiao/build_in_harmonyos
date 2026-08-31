#!/usr/bin/env python3
"""Conan test_package for collectd — verifies plugin API headers compile.

collectd 是 header-only 依赖包（无库可链接），test_package 按 collectd-apk
插件的编译方式（-I<include/collectd/core> + <daemon/plugin.h>）编译测试程序，
验证头文件布局与依赖链完整（R34 语义：实质使用被测包 API——插件注册接口）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CollectdTestConan(ConanFile):
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
        # R-CI L0d: test() 必须含 self.run() 直跑测试程序
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_collectd")
        self.run(bin_path, env="conanrun")
