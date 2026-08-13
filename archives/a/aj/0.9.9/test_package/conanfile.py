#!/usr/bin/env python3
"""Conan test_package for aj 0.9.9 — 验证 aj-snapshot 工具可执行。

aj 是 C 命令行工具（application），test_package 编译 test_aj.c 并运行
（argv 传 aj-snapshot 路径，执行 "aj-snapshot -h" 校验 usage 输出）。
R34 反空壳：C 测试二进制真实调用被测包二进制，而非空壳 return 0。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class AjTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        # L0c 门禁要求 test_package 有测试源文件：test_aj.c 真实编译（R34
        # 反空壳——test_aj.c 通过 system() 执行 aj-snapshot -h 校验 usage）
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        aj_bin = os.path.join(self.dependencies["aj"].package_folder,
                              "bin", "aj-snapshot")
        if not os.path.exists(aj_bin):
            raise ConanException(f"aj-snapshot binary not found: {aj_bin}")
        if cross_building(self):
            self.output.info("cross-building: 编译验证通过，跳过运行时测试")
            return
        bindirs = self.cpp.build.bindirs
        if not bindirs:
            raise ConanException("test_aj build folder (bindirs) is empty — cannot locate test binary")
        test_bin = os.path.join(bindirs[0], "test_aj")
        # test_aj.c 用 argv 传 aj-snapshot 路径（避依赖 PATH 巧合 + shell 注入防护）
        self.run(f'"{test_bin}" "{aj_bin}"', env="conanrun")
        self.output.info("aj test PASSED (aj-snapshot -h prints usage)")
