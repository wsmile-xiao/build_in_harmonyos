#!/usr/bin/env python3
"""Conan test_package — mlddc 1.0-1 消费者测试 (10 条断言)。

CMake 编译并运行 test.c：消费包内 bin/mlddc、bin/mlupd、bin/mymldata 与文档，
覆盖 ELF 头 / 目标架构 / 可执行类型 / 真实执行退出码 / 脚本 shebang / 数据模板。
非 OHOS 目标（如 Windows 开发机）自动跳过，CI 在 OHOS runner 上真实执行。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class MlddcTestConan(ConanFile):
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
        if not can_run(self):
            self.output.info("Skipping runtime test on non-runnable target "
                             "(aarch64 OHOS hardware required).")
            return
        package_folder = self.dependencies["mlddc"].package_folder
        test_exe = os.path.join(self.cpp.build.bindir, "test_mlddc")
        self.run(f'"{test_exe}" "{package_folder}"')
