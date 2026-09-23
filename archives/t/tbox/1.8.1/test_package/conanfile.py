#!/usr/bin/env python3
"""Conan test_package for tbox 1.8.1 — 消费者视角验证（Conan L1）。

CI 通过 `conan create` 自动调用本 test_package：构建一个真实的消费者程序，
链接被测 libtbox.a，并断言产物自报的版本号与各模块行为。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class TboxTestConan(ConanFile):
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
        # OHOS: /system/bin/sh (mksh) 不能直接执行 ELF，用 bash 包一层
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_tbox'", env="conanrun")
