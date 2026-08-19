#!/usr/bin/env python3
"""Conan test_package for akku 1.1.0 — version smoke test."""
import os

from conan import ConanFile
from conan.tools.build import can_run


class AkkuTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            # 冒烟测试：akku 用 version 子命令（非 --version，srfi-37 args-fold），
            # 校验输出包含 1.1.0。脚本在 test_package/test.sh（L0c 测试源文件）。
            script = os.path.join(os.path.dirname(__file__), "test.sh")
            shell = os.environ.get("CONFIG_SHELL") or "/bin/sh"
            # 路径可能含空格/括号（如目录名 "xx (1)"），加引号防止 shell 解析错误
            self.run(f'"{shell}" "{script}"', env="conanrun")
