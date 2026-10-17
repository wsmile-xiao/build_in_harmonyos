#!/usr/bin/env python3
"""Installed-package consumer tests for rlog 1.4 (L1 test_package).

构建并运行一个消费者程序，真实调用 librlog 的公开 API：版本符号
（RLogVersion/CURRENT_RLOG_VERSION）、通道注册与命名、RLogNode 订阅-发布链路、
通道层级投递与无关通道过滤、消息格式化、rAssert → rlog::Error 的源码位置、
计时 API（rlog_get_time/rlog_time_diff/rlog_time_unit），共 11 项断言。

布局：使用 Conan 的 cmake_layout —— CMakeDeps/CMakeToolchain/VirtualRunEnv 的生成
物与 CMake 缓存全部落在 `test_package/build/<配置>/` 下，由仓库根 .gitignore 的
`build/` 规则忽略；包目录内不另放 .gitignore。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class RlogTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    exports_sources = "CMakeLists.txt", "*.cpp"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            raise ConanException("rlog consumer test cannot run on this platform")
        binary = os.path.join(self.cpp.build.bindirs[0], "test_rlog")
        if not os.path.isfile(binary):
            raise ConanException(f"consumer binary is missing: {binary}")
        self.run(f'"{binary}"', env="conanrun")
