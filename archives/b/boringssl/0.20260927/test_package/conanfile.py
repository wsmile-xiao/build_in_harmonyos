#!/usr/bin/env python3
"""Conan test_package — boringssl/0.20260927.

L1 消费者测试（conan create 自动执行）+ R34 实质 API 测试 + R53 鸿蒙特有断言。

  - build():  编译 test_boringssl.cc（真实调用 BoringSSL API 的 E2E 用例）
  - test():   1) ctest 运行 R34 消费者程序
              2) ohos_specific_test.py 运行 R53 鸿蒙特有断言
                 （静态交付 / ELF aarch64 + musl / 无 RPATH / bssl 实跑）
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class BoringSSLTestConan(ConanFile):
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
        # R34: 消费者程序真实调用被测包 API（TLS1.3 握手 / BN / SHA-256 / RAND）
        cmake = CMake(self)
        cmake.test()

        # R53: 鸿蒙特有测试（至少一个：实际运行 + 断言鸿蒙适配路径）
        pkg = self.dependencies["boringssl"].package_folder
        script = os.path.join(self.source_folder, "ohos_specific_test.py")
        self.run(f'python3 "{script}" --pkg "{pkg}"', env="conanrun")
