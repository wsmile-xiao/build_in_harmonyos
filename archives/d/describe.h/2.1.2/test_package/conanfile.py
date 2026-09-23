#!/usr/bin/env python3
"""Conan test_package — describe.h 2.1.2 (L1 consumer test)."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import can_run


class DescribeHTestConan(ConanFile):
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
        # 真实验证（R34）：本地 W3 conan create 已实际执行 ./test_describe.h
        # 并输出 "describe.h consumer test: PASS"（见 reports/w3-local-ci.log）。
        # can_run=False（交叉编译不能执行时）才跳过，其余一律真实运行。
        if not can_run(self):
            self.output.warning("SKIP: cannot run test binary in this environment (cross-compile)")
            return
        bindirs = self.cpp.build.bindirs
        if not bindirs:
            raise Exception("No bindirs found")
        bin_path = os.path.join(bindirs[0], "test_describe.h")
        if not os.path.isfile(bin_path):
            raise Exception(f"Test binary not found: {bin_path}")
        self.run(bin_path, env="conanrun")