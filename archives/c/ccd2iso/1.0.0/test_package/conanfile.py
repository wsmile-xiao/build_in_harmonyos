#!/usr/bin/env python3
"""Test package — ccd2iso 1.0.0.

R34: test_package must make substantive use of the tested package.
ccd2iso is a CLI tool; the C test binary runs `ccd2iso --version` and
`--help`, checking exit code 0 and non-empty output (sandbox has no CD
image to convert, so runnability is verified via CLI options).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class Ccd2isoTestConan(ConanFile):
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
        test_bin = os.path.join(self.cpp.build.bindir, "test_ccd2iso")
        ccd2iso_bin = os.path.join(self.dependencies["ccd2iso"].package_folder, "bin", "ccd2iso")
        self.run(f"{test_bin} {ccd2iso_bin}", env="conanrun")
