#!/usr/bin/env python3
"""Conan test_package for construct 2.10.70 — import + real API test."""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class ConstructTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            python_exe = sys.executable
            # 显式注入 package 的 site-packages 到 PYTHONPATH（与 soupsieve/pyxdg
            # 同款：conanrun 环境的 PYTHONPATH 注入实测不生效，手动注入可靠）
            pkg = self.dependencies["construct"].package_folder
            py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
            site = os.path.join(pkg, "lib", py_ver, "site-packages")
            test_script = os.path.join(os.path.dirname(__file__), "test_construct.py")
            self.run(f'PYTHONPATH="{site}" {python_exe} "{test_script}"',
                     env="conanrun")
