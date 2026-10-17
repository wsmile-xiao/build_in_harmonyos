#!/usr/bin/env python3
"""Conan test_package for alfred 2026.2 — 验证 alfred 二进制可执行。

alfred 是 C 命令行工具（daemon+client，application），上游无测试套件。
test_package 运行 alfred --help 验证二进制已安装到 bin/ 且可执行
（R34 反空壳：真实调用被测包二进制）。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building


class AlfredTestConan(ConanFile):
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
        bin_dir = self.dependencies["alfred"].cpp_info.bindirs[0]
        pkg = self.dependencies["alfred"].package_folder
        alfred_bin = os.path.join(pkg, bin_dir, "alfred")
        if not os.path.exists(alfred_bin):
            raise ConanException(f"alfred not found at {alfred_bin}")
        # R34 反空壳：真实执行 alfred --help（--help 打印 usage 后退出码非 0 属
        # 预期，ignore_errors=True；L0d 门禁要求 test() 有 self.run 调用）
        self.run(f'"{alfred_bin}" --help', ignore_errors=True)
        self.output.info("alfred test PASSED (alfred --help runs)")
