#!/usr/bin/env python3
"""Conan test_package — cajun-jsonapi 2.1.1 消费者验证 (C++ header-only).

通过 Conan 包消费公开头文件 <cajun/json/...>，验证第三方使用者
可以编译、链接并调用 json::Reader/Writer API 得到正确结果；
test_ohos 为鸿蒙专项测试（UTF-8 / 双精度 / 异常路径 / 嵌套往返）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CajunJsonapiTestConan(ConanFile):
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
        # 直接运行二进制以确保真实执行
        bindir = self.cpp.build.bindirs[0]
        self.run(os.path.join(bindir, "test_cajun_jsonapi"), env="conanrun")
        self.run(os.path.join(bindir, "test_ohos"), env="conanrun")
