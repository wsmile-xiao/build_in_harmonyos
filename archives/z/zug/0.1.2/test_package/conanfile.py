#!/usr/bin/env python3
"""Conan test_package — zug 0.1.2 消费者视角验证。

只 require 被测包，不显式声明 boost：验证 zug 的 transitive_headers 真正把
boost 头文件带给消费者（zug 公开头文件里裸用 #include <boost/...>）。
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class ZugTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
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
            # 交叉构建时消费者程序只编译不执行，必须留 WARNING 而不是 info，
            # 避免「没跑」被读成「跑过了」。
            self.output.warning(
                "cross_building=True：test_zug / test_zug_ohos 未执行，需真机复验")
            return
        # 通用消费者测试 + 鸿蒙专项（跨翻译单元）测试
        for prog in ("test_zug", "test_zug_ohos"):
            self.run(os.path.join(self.cpp.build.bindirs[0], prog),
                     env="conanrun")
