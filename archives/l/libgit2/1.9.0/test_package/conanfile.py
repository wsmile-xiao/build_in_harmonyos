#!/usr/bin/env python3
"""Conan test_package — libgit2 1.9.0 消费者验证 (R34 真实 API)。

消费者视角测试：编译链接 libgit2::libgit2，运行 test_libgit2，
调用 git_libgit2_version / git_libgit2_init / git_libgit2_opts /
git_repository_init 验证库可用（HMDFS 属主校验已适配关闭）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Libgit2TestConan(ConanFile):
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
        cmake = CMake(self)
        cmake.test()
        # Alternatively, run the binary directly:
        # self.run(f"{os.path.join(self.cpp.build.bindirs[0], 'test_libgit2')}", env="conanrun")
