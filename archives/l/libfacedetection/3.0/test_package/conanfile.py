#!/usr/bin/env python3
"""Conan test_package — libfacedetection 3.0 消费者验证。

真实调用库的 facedetect_cnn 人脸检测 API（非空壳，R34/PF3/L0d）：
构建后直接以 self.run() 执行 test_libfacedetection 二进制（ctest 方式
由 CI 的 L0d 要求 self.run 兜底）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibfacedetectionTestConan(ConanFile):
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
        # 直接运行测试二进制（L0d 要求 test() 含 self.run 实际执行）
        binary = os.path.join(self.cpp.build.bindirs[0], "test_libfacedetection")
        self.run(binary, env="conanrun")
