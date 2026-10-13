#!/usr/bin/env python3
"""Conan test_package for ubelt 1.4.0 — 消费者视角验证.

执行两个真实测试脚本（均满足 L0c：test() 内有 self.run 实际执行逻辑）：
  1. test_ubelt.py        — 公开 API 功能测试（R34：真实调用被测包 API）
  2. test_ohos_ubelt.py   — 鸿蒙特有测试（OHOS 平台契约，数量 ≥1）
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException


class UbeltTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["ubelt"].package_folder
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(pkg, "lib", py_ver, "site-packages")
        if not os.path.isdir(os.path.join(site, "ubelt")):
            raise ConanException(f"ubelt package missing under {site}")

        base = os.path.dirname(__file__)
        for tname in ("test_ubelt.py", "test_ohos_ubelt.py"):
            script = os.path.join(base, tname)
            if not os.path.isfile(script):
                raise ConanException(f"{tname} missing: {script}")
            self.run(f'python3 "{script}" "{site}"')
