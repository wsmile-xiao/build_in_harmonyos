#!/usr/bin/env python3
"""Conan test_package — tau 1.0.0 (Muon header-only) consumer validation.

L0d 门禁要求 test() 必须包含真实 self.run(...) 调用执行已构建的测试二进制；
test_package 通过公开头文件 <Muon/Muon.h> 编译链接 tau::tau 后运行断言套件。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class TauTestConan(ConanFile):
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
        # 真实执行已构建的消费者测试二进制（L0d：必须含 self.run 调用）
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_tau"), env="conanrun")
        # 鸿蒙专项测试（OHOS 工具链/运行时验证）
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_tau_ohos"), env="conanrun")
