#!/usr/bin/env python3
"""Conan test_package — cxxgraph 4.1.0 消费者验证 (C++ header-only).

通过 Conan 包消费 CXXGraph.hpp 的公开 API（节点/边/图/Dijkstra），
验证第三方使用者可编译、链接、调用并得到正确业务结果。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CxxgraphTestConan(ConanFile):
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
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_cxxgraph"), env="conanrun")
