#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/{letter}/cn-cbor/{version}/test_package/conanfile.py
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CncborTestConan(ConanFile):
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
        # OHOS: /system/bin/sh (mksh) 无法直接执行 ELF 二进制。
        # 用 bash 包装消费者测试程序执行（形态同 zlib/1.3.1 test_package），
        # env="conanrun" 加载被测包运行时环境（R33：不裸用 ${CC}/${CFLAGS}）。
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_cn-cbor'", env="conanrun")
