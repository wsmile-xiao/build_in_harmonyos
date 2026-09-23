#!/usr/bin/env python3
"""test_package for telepathy-glib — R34 实质产物校验.

test.c 调用不依赖运行环境的纯 API（tp_g_value_slice_new_boolean 等 util 函数 +
tp_errors_quark 错误域注册），验证库可链接、公开 API 可调用。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import cross_building


class TelepathyGlibTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not cross_building(self):
            bin_path = os.path.join(self.cpp.build.bindirs[0], "test_telepathy_glib")
            self.run(bin_path, env="conanrun")
