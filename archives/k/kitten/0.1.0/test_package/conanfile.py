#!/usr/bin/env python3
"""Conan test_package — kitten 0.1.0 消费者测试（L1）。

R34：``test()`` 必须真实执行被测物（``self.run`` 直跑消费者二进制）。
不写空壳：不用 echo/print 型占位，也不依赖 ``assert``/``NDEBUG`` 判定结果。
消费者从**已安装包头** ``#include <kitten/...>``（不是源码树）实调 functor / monad /
applicative / function_wrapper / multifunctor 五类实例面，显式计数 21 项、任一失败
进程非零退出；输出 ``kitten consumer checks: 21 run, 0 failed``。
"""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class KittenTestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info(
                "Cross-building: consumer test is executed by the device-side verification"
            )
            return
        executable = os.path.join(self.cpp.build.bindir, "test_kitten")
        self.run(f'"{executable}"', env="conanrun")
