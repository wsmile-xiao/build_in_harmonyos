#!/usr/bin/env python3
"""Conan test_package — EAAssert L1 消费者测试（HarmonyOS PC）。

通过 conan create 自动运行：仅使用 EAAssert 安装后的公开头文件
(<EAAssert/eaassert.h>)、公开 API（EA::Assert::SetFailureCallback/
GetFailureCallback）与链接目标 libEAAssert，验证第三方业务组件在
OHOS (aarch64-linux-ohos) 上可编译、链接、调用并正常运行。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class EaassertTestConan(ConanFile):
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
        # 直接运行二进制兜底（ctest 注册失败时仍有退出码）
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_eaassert")
        if os.path.exists(bin_path):
            self.run(bin_path, env="conanrun")