#!/usr/bin/env python3
"""test_package — backport-cpp 1.2.0 消费者测试（L1 / PF3 真实执行）。

消费者只用**已安装的包**（不碰上游源码树）：一个 TU 包含全部 16 个公开头，
再对 optional/variant/string_view/span/any/tuple/utility/functional/iterator/
memory/type_traits/exception/chrono/complex/string 共 35 条运行期断言逐条校验，
程序自报 `PASS: ... 35/35 断言通过`，任一失败即退出码非 0（另有 3 条编译期
static_assert 只做编译期保障，不计入运行期总数）。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class BackportCppTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.user_presets_path = False
        # 上游库以 C++11 为最低标准，消费者按库自身声明的标准编译
        tc.cache_variables["CMAKE_CXX_STANDARD"] = 11
        tc.cache_variables["CMAKE_CXX_STANDARD_REQUIRED"] = True
        tc.cache_variables["CMAKE_CXX_EXTENSIONS"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: skip consumer runtime test")
            return
        consumer = os.path.join(self.cpp.build.bindirs[0], "test_backport_cpp")
        self.run('"%s"' % consumer)
