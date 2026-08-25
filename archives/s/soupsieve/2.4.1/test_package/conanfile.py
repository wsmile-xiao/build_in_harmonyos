#!/usr/bin/env python3
"""Conan test_package for soupsieve 2.4.1 — import + real API test."""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class SoupsieveTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            python_exe = sys.executable
            # soupsieve 运行时依赖 bs4（__init__.py:34 / css_match.py:8 顶层
            # import bs4——2.x 系列均如此，soupsieve 本就是 beautifulsoup4 的
            # CSS 引擎组件；CI 干净环境无 bs4 实测 import 失败）——测试环境
            # pip 装 beautifulsoup4（提供 bs4 模块，模拟真实使用场景：bs4
            # 装好后 soupsieve import 可用）
            self.run(
                f'{python_exe} -m pip install --break-system-packages '
                f'--timeout 120 --retries 3 beautifulsoup4',
                env="conanrun")
            # 显式注入 package 的 site-packages 到 PYTHONPATH
            # （conanrun env 的 PYTHONPATH 注入实测不生效——soupsieve 先例）
            pkg = self.dependencies["soupsieve"].package_folder
            py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
            site = os.path.join(pkg, "lib", py_ver, "site-packages")
            test_script = os.path.join(os.path.dirname(__file__), "test_soupsieve.py")
            self.run(f'PYTHONPATH="{site}" {python_exe} "{test_script}"',
                     env="conanrun")
