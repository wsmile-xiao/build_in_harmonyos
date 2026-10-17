#!/usr/bin/env python3
"""Conan test_package — lib_fts 1.2.8 L1 测试（消费者视角，真实调用公开 API）。

仅通过已安装的公开头文件 <fts_fuzzy_match.h> 调用 fts::fuzzy_match 与
fts::fuzzy_match_simple，验证第三方使用者可编译、链接并得到正确结果。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibftsTestConan(ConanFile):
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
        cmake.test()
        # 直接运行三个二进制（ctest 之外再各跑一次，输出真实 stdout）
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_lib_fts"), env="conanrun")
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_lib_fts_ohos"), env="conanrun")
        # 端到端消费者用例：以查询词 "wlan" 驱动完整业务流（查询->匹配->排序->打开设置页）
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_lib_fts_e2e") + " wlan", env="conanrun")