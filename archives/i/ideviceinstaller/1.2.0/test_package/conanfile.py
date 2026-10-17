#!/usr/bin/env python3
"""Test package — ideviceinstaller 1.2.0.

R34: test_package must make substantive use of the tested package.
ideviceinstaller is a CLI tool; the C test binary runs `--version` and
`--help`, checking exit code 0 and non-empty output (sandbox has no iOS
device to manage, so runnability is verified via CLI options).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class IdeviceinstallerTestConan(ConanFile):
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
        # R-CI L0d: test() 必须含 self.run() 直跑测试程序
        # can_run() 守卫：交叉编译时跳过运行时测试（二进制为交叉架构）
        if not can_run(self):
            self.output.info("Skipping test: cross-building build platform cannot run target binaries")
            return
        test_bin = os.path.join(self.cpp.build.bindir, "test_ideviceinstaller")
        idev_bin = os.path.join(self.dependencies["ideviceinstaller"].package_folder, "bin", "ideviceinstaller")
        self.run(f"{test_bin} {idev_bin}", env="conanrun")
