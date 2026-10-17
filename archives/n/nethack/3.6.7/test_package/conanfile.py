#!/usr/bin/env python3
"""Test package for nethack 3.6.7 — Conan L1 smoke test.

运行 nethack --version，验证可执行文件存在且能正常启动。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class NethackTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            binary = os.path.join(
                self.dependencies["nethack"].package_folder, "bin", "nethack"
            )
            self.run(f'"{binary}" --version', env="conanrun")