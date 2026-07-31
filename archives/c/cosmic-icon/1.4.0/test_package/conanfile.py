#!/usr/bin/env python3
"""Conan test_package — cosmic-icon 1.4.0

编译并运行 test_icons 验证图标主题包安装到目标路径后：
  1. 图标目录存在
  2. 至少有 1 个非空 SVG 图标文件
通过 self.run() 实跑测试程序，满足 R34 + L0 stub_test_method 门禁。
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class CosmicIconTestConan(ConanFile):
    settings = "os", "compiler", "arch", "build_type"
    test_type = "explicit"
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
        if cross_building(self):
            self.output.info("cross-building: 编译验证通过，跳过运行时测试")
            return
        icon_dir = os.path.join(self.dependencies["cosmic-icon"].package_folder,
                                "share", "icons", "Cosmic")
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_icons")
        self.run(f'"{test_bin}" "{icon_dir}"', env="conanrun")
