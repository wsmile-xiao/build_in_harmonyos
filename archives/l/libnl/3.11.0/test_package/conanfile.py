#!/usr/bin/env python3
"""Conan test_package — libnl 3.11.0 消费者视角编译 / 链接 / 运行验证。

实质测试（非空壳）：test_libnl.c 真实调用 libnl 的 6 个交付子库导出符号并断言
结果（R34：test_package 必须实质依赖被测包）。交叉编译场景下同架构无法运行目标
二进制，故仅在 OHOS（本机即目标平台）与 Linux 上执行。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibnlTestPackageConan(ConanFile):
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
        # R32：平台判断用 in，不用 ==
        if self.settings.os not in ("Linux", "OHOS"):
            self.output.info(f"skip runtime test on {self.settings.os} (cross-compiled)")
            return
        exe = os.path.join(self.cpp.build.bindirs[0], "test_libnl")
        self.run(exe, env="conanrun")
