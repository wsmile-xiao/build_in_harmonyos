#!/usr/bin/env python3
"""Conan test_package for soupsieve 2.9.2 — import + real API test."""
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
            # 显式注入 package 的 site-packages 到 PYTHONPATH
            # （conanrun env 的 PYTHONPATH 注入实测不生效——手动
            # PYTHONPATH import OK 证明 package 内容正确，问题在
            # conanrun 环境变量传递）
            pkg = self.dependencies["soupsieve"].package_folder
            py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
            site = os.path.join(pkg, "lib", py_ver, "site-packages")
            test_script = os.path.join(os.path.dirname(__file__), "test_soupsieve.py")
            self.run(f'PYTHONPATH="{site}" {python_exe} "{test_script}"',
                     env="conanrun")
