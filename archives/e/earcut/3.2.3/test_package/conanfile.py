#!/usr/bin/env python3
"""Conan test_package — earcut 3.2.3 (header-only consumers smoke test).

两个真实可执行测试（均调用被测包 API，R34）：
  1. test_earcut: 消费者基础三角剖分（方形+洞，验证索引数与面积守恒）
  2. test_earcut_ohos: HarmonyOS 专项测试（大坐标瓦片级多边形 + 首环退化等场景）
运行于 OHOS aarch64 本机（conan create 时 test() 实际执行）。
"""
import os
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.build import cross_building


class EarcutTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: skip runtime test")
            return
        for exe in ("test_earcut", "test_earcut_ohos"):
            self.run(os.path.join(self.cpp.build.bindirs[0], exe), env="conanrun")