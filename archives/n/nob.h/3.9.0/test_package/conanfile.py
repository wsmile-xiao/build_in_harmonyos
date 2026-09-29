#!/usr/bin/env python3
"""Conan test_package — nob.h 3.9.0 消费者验证。

以第三方使用者身份通过安装后的公开头文件 nob.h（NOB_IMPLEMENTATION）
使用 string-view / dynamic-array / temp-printf 公共 API，断言可观察结果，
验证头文件可编译、可链接、可运行（R34：真实调用被测物，非空壳）。
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class NobHTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "VirtualRunEnv"

    def configure(self):
        self.settings.rm_safe("os.version")

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.15"
        tc.generate()

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        exe_dir = self.cpp.build.bindirs[0]
        if cross_building(self):
            self.output.info("cross-building: consumer compiled but not run")
            return
        # 消费者用例：仅通过公开头文件/API 使用 nob.h
        self.run(os.path.join(exe_dir, "test_nob_consumer"), env="conanrun")
        # 鸿蒙专项测试：OHOS 目标下库的内存/字符串/UTF-8 边界行为验证
        self.run(os.path.join(exe_dir, "test_nob_ohos"), env="conanrun")
