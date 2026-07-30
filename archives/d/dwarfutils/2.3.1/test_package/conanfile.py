#!/usr/bin/env python3
"""Conan test_package — dwarfutils L1 test.

R34: test_package 必须实质调用被测包的 API。
dwarfutils 同时提供库和工具：
- 库验证：find_package(dwarfutils) + target_link_libraries
- 工具验证：dwarfdump --version
"""
import os
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class DwarfutilsTestConan(ConanFile):
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
        # 交叉编译守卫：在 OHOS aarch64 交叉编译场景下，
        # aarch64 二进制无法在 x86_64 主机上执行，跳过运行时测试
        if not can_run(self):
            return

        # 验证 1: 运行编译的 test_dwarfutils 二进制（实质调用 libdwarf API）
        test_bin = os.path.join(self.cpp.build.bindir, "test_dwarfutils")
        self.run(test_bin, env="conanrun")

        # 验证 2: dwarfdump --version 验证工具二进制可执行
        #（注：libdwarf 的 bindirs 在 conanrun 环境中可能不自动注入 PATH）
        dwarfdump_bin = os.path.join(self.dependencies["dwarfutils"].package_folder, "bin", "dwarfdump")
        self.run(f"{dwarfdump_bin} --version")
