#!/usr/bin/env python3
"""Conan test_package for speg 0.3 — consumer test (R34).

Runs test_speg.py (standalone test source, satisfies L0c) via self.run with
env="conanrun" (conanrun 注入 PYTHONPATH——见 zipp/yarl 先例——否则 python3
拿不到 lib/python3/speg）。test_speg.py 实质调用 speg 的 PEG API：
speg.peg() 解析简单文法 + ParseError 路径；另含 1 个端到端消费者用例
（rule12）：INI 风格多行配置文法解析 → 数据提取 → 坏输入 ParseError 行定位。
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException


class SpegTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["speg"].package_folder
        site = os.path.join(pkg, "lib", "python3")
        if not os.path.isdir(os.path.join(site, "speg")):
            raise ConanException(f"speg package missing under {site}")
        test_script = os.path.join(os.path.dirname(__file__), "test_speg.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_speg.py missing: {test_script}")
        self.run(
            f'PYTHONPATH="{site}" {sys.executable} "{test_script}"',
            env="conanrun")
