#!/usr/bin/env python3
"""Conan test_package for reflect-cpp 0.17.0 — L1 官方测试 + HarmonyOS 专项测试.

验证下游 C++ 程序可包含 reflect-cpp 头文件并实际调用
rfl::json 序列化/反序列化 API（消费方视角验证，非空壳）。
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class ReflectCppTestConan(ConanFile):
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
        # 直接执行测试二进制（L0d/PF3 门禁要求 self.run 实际执行逻辑）
        self.run(
            os.path.join(self.cpp.build.bindirs[0], "test_reflect_cpp"),
            env="conanrun",
        )
        # HarmonyOS 专项测试入口：平台宏确认 + JSON 往返实测
        self.run(
            os.path.join(self.cpp.build.bindirs[0], "harmonyos_specific_test"),
            env="conanrun",
        )
