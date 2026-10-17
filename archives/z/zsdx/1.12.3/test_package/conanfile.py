#!/usr/bin/env python3
"""Conan test_package — zsdx 1.12.3（真实数据完整性验证）。

zsdx 是纯数据包：无可链接产物，也没有可实跑的引擎（Solarus 引擎不在官方仓，
见 ../notes.md）。可验证物是安装出来的 data.solarus——断言脚本在 OHOS 目标上
实跑，对 zip 做全量 CRC 校验 + 条目数/类型学/根条目契约/quest 元数据断言。
"""
import os
import sys

from conan import ConanFile


class ZsdxTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["zsdx"].package_folder
        test_script = os.path.join(os.path.dirname(__file__), "test_zsdx.py")
        self.run(f'"{sys.executable}" "{test_script}" "{package_folder}"')
