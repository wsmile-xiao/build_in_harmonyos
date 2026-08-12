#!/usr/bin/env python3
"""Conan test_package for aegean 0.16.0 — 验证 parseval 工具可执行。

aegean 是 C 工具集（application），test_package 编译 test_aegean.c 并运行
（argv 传 parseval 路径，执行 parseval --help 验退出码）。R34 反空壳：
C 测试二进制真实调用被测包二进制，而非空壳 return 0。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class AegeanTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        # L0c 门禁要求 test_package 有测试源文件：test_aegean.c 真实编译（R34
        # 反空壳——test_aegean.c 通过 system() 执行 parseval --help 校验退出码）
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        parseval = os.path.join(self.dependencies["aegean"].package_folder,
                                "bin", "parseval")
        if not os.path.exists(parseval):
            raise ConanException(f"parseval binary not found: {parseval}")
        if cross_building(self):
            self.output.info("cross-building: 编译验证通过，跳过运行时测试")
            return
        bindirs = self.cpp.build.bindirs
        if not bindirs:
            raise ConanException("test_aegean build folder (bindirs) is empty — cannot locate test binary")
        test_bin = os.path.join(bindirs[0], "test_aegean")
        # test_aegean.c 用 argv 传 parseval 路径（避依赖 PATH 巧合 + shell 注入防护）
        self.run(f'"{test_bin}" "{parseval}"', env="conanrun")
        self.output.info("aegean test PASSED (parseval --help runs)")
