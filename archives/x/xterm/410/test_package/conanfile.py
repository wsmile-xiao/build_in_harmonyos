#!/usr/bin/env python3
"""Conan test_package — xterm 410 L1 测试

xterm 是终端工具（非库），测试验证二进制存在即可。
"""
import os

from conan import ConanFile


class XtermTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # xterm 需要 X server 才能运行，无头环境仅验证二进制存在
        pkg_dir = self.dependencies["xterm"].package_folder
        bin_dir = os.path.join(pkg_dir, "bin")
        assert os.path.isdir(bin_dir), f"bin/ not found in {pkg_dir}"
        assert os.path.isfile(os.path.join(bin_dir, "xterm")), "xterm binary not found"
        print(f"✅ xterm binary found at {bin_dir}/xterm")
