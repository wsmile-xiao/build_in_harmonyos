#!/usr/bin/env python3
"""Conan test_package — 真实调用 hyphen 公开 API 的消费者验证（L1 测试）。

CI 通过 `conan create` 自动运行本测试。测试程序 test_hyphen 从已安装
包的 share/hyphen/ 加载 hyph_en_US.dic，调用 hnj_hyphen_load /
hnj_hyphen_hyphenate2 / hnj_hyphen_free 验证断词输出。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class HyphenTestConan(ConanFile):
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
        # 已安装包的数据目录：share/hyphen/hyph_en_US.dic
        pkg = self.dependencies["hyphen"].package_folder
        dict_path = os.path.join(pkg, "share", "hyphen", "hyph_en_US.dic")
        # cmake_layout 下二进制位于 build_folder；不用 self.cpp.build.bindirs
        # （test_package 场景该列表为空，os.path.join 遇绝对路径会丢失前缀）
        binary = os.path.join(self.build_folder, "test_hyphen")
        self.run('"%s" "%s"' % (binary, dict_path), env="conanrun")
