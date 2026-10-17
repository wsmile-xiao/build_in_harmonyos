#!/usr/bin/env python3
"""Conan test_package for soplex 3.1.1 — Conan L1 consumer test.

Builds a small LP through the public SoPlex C++ API, solves it, and verifies
the objective value. This proves headers, static lib linking and the solver
runtime work for a downstream consumer (R34: must call the library API).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class SoplexTestConan(ConanFile):
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
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # 消费者用例：公开 API 构建并求解 LP，校验最优目标值
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_soplex")
        self.run(f"{bash} -c '{bin_path}'", env="conanrun")
        # 鸿蒙专项测试：aarch64-ohos 平台属性（ELF e_machine）+ 公开 API 求解
        ohos_path = os.path.join(self.cpp.build.bindirs[0], "test_ohos_soplex")
        self.run(f"{bash} -c '{ohos_path}'", env="conanrun")
