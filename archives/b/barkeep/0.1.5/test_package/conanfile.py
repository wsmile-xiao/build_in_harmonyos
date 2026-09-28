#!/usr/bin/env python3
"""Conan test_package — barkeep 0.1.5 消费者测试（L1）。

R34：``test()`` 必须真实执行被测物（``self.run`` 直跑消费者二进制）。
不写空壳：不用 echo/print 型占位，也不依赖 ``assert``/``NDEBUG`` 判定结果。
消费者从**已安装包头** ``#include <barkeep/barkeep.h>``（不是源码树），在无 TTY
（管道输出——鸿蒙设备 HiShell 与 CI worker 的真实执行形态）下走 ``no_tty`` 渲染
路径断言输出内容，显式计数、任一失败进程非零退出。
"""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class BarkeepTestPackageConan(ConanFile):
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
        executable = os.path.join(self.cpp.build.bindir, "test_barkeep")
        self.run(f'"{executable}"', env="conanrun")
