#!/usr/bin/env python3
"""Test package — cookiecutter 2.7.1 (python)"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class CookiecutterTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        # cookiecutter 自身只打包 cookiecutter/ 模块 + bin/cookiecutter launcher,
        # 运行时依赖 (Jinja2/click/requests/...) 不在此包内,
        # 因此仅验证模块可导入 + CLI 入口脚本存在 (见 test.py).
        cookiecutter_dep = self.dependencies[self.tested_reference_str]
        bindir = cookiecutter_dep.cpp_info.bindirs[0]
        self.run(f'"${{PYTHON:-python3}}" test.py "{bindir}"', env="conanrun")
