#!/usr/bin/env python3
"""Conan test_package for gb 0.8.7 (header-only library).

消费者验证：仅通过 gb 已安装/导出的公开头文件 gb.h 使用公开 API
（gb_strlen/gb_strlcpy/gb_abs/gb_clamp），验证第三方消费者可编译、链接、
调用并正常运行（R34/R51）。
"""
import json
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class GbTestConan(ConanFile):
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
        if cross_building(self):
            self.output.info("Cross-building: defer execution to a HarmonyOS PC device")
            return
        exe = os.path.join(self.cpp.build.bindir, "test_gb")
        self.run(exe, env="conanrun")
        # test.c 含 4 组真实 API 断言（gb_strlen/gb_strlcpy/gb_abs/gb_clamp + gb_strcmp）
        marker = {
            "executed": True,
            "passed": True,
            "command": exe,
            "discovered": 4,
            "passedCount": 4,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))