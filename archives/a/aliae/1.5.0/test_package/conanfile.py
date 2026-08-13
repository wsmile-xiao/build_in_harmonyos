#!/usr/bin/env python3
"""Conan test_package for aliae 1.5.0 — 验证 aliae 二进制可执行。

aliae 是 Go 命令行工具（application），上游测试已在 build() 阶段运行
（go test ./... 15 个测试全部通过）。test_package 运行 aliae --help
验证二进制已安装到 bin/ 且可执行（R34 反空壳：真实调用被测包二进制）。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building


class AliaeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        from conan.tools.layout import basic_layout
        basic_layout(self)

    def build(self):
        pass

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: skip runtime test")
            return
        bin_dir = self.dependencies["aliae"].cpp_info.bindirs[0]
        pkg = self.dependencies["aliae"].package_folder
        aliae_bin = os.path.join(pkg, bin_dir, "aliae")
        if not os.path.exists(aliae_bin):
            raise ConanException(f"aliae not found at {aliae_bin}")
        # R34 反空壳：真实执行 aliae --help（L0d 门禁要求 test() 有 self.run 调用）
        self.run(f'"{aliae_bin}" --help')
        self.output.info("aliae test PASSED (aliae --help runs)")
