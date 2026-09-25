#!/usr/bin/env python3
"""test_package/conanfile.py — usbrelay 1.0 消费者测试驱动。

编译 test.c（真实链接 usbrelay::usbrelay 并调用公开 C API），ctest + 直跑
双路径执行 5 组断言。运行环境挂 conanrun：libusbrelay.so 的 DT_NEEDED
libhidapi-libusb 经依赖包 lib 目录解析。
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class UsbrelayTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

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
        # L0d 显式直跑路径（与 ctest 同源断言，退出码判定）
        exe = os.path.join(self.cpp.build.bindirs[0], "test_usbrelay")
        self.run(f'"{exe}"', env="conanrun")
