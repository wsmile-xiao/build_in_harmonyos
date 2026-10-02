#!/usr/bin/env python3
"""Conan test_package — schism 鸿蒙特有消费者测试。

CI 通过 conan create 自动调用。test() 将随包 schismtracker 二进制路径
注入 SCHISM_BIN，测试程序实际执行 --version / --help 验证产物可执行性
与 CLI 契约（schismtracker 为交互式 TUI 程序，无显示环境时 version/help
是其消费者可验证契约）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class SchismTestConan(ConanFile):
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
        bindir = self.dependencies["schism"].cpp_info.bindirs[0]
        pkg_bin = os.path.join(self.dependencies["schism"].cpp_info.bindirs[0],
                               "schismtracker")
        # conan 包内 bin/schismtracker 的绝对路径解析
        import glob
        candidates = glob.glob(os.path.join(
            self.dependencies["schism"].package_folder, "**", "schismtracker"),
            recursive=True)
        bin_path = candidates[0] if candidates else pkg_bin
        env = f"SCHISM_BIN={bin_path}"
        self.run(f"{env} {os.path.join(self.cpp.build.bindirs[0], 'test_schism')}",
                 env="conanrun")
