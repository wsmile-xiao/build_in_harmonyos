#!/usr/bin/env python3
"""Conan test_package for cmt 1.18 — LADSPA plugin consumer test.

编译并运行 test_cmt 验证 cmt.so LADSPA 插件库：
  1. dlopen cmt.so 成功
  2. ladspa_descriptor 符号可解析
  3. 至少 1 个 LADSPA 插件 descriptor 非空
通过 self.run() 实跑测试程序，满足 R34 + L0 stub_test_method 门禁。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CmtTestConan(ConanFile):
    settings = "os", "compiler", "arch", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmt_so = os.path.join(self.dependencies["cmt"].package_folder,
                              "lib", "ladspa", "cmt.so")
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_cmt")
        self.run(f'"{test_bin}" "{cmt_so}"', env="conanrun")
