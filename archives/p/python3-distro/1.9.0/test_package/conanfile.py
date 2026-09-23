#!/usr/bin/env python3
"""Conan test_package for python3-distro 1.9.0 — consumer test + CLI smoke test."""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class Python3DistroTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            python_exe = sys.executable
            test_script = os.path.join(
                os.path.dirname(__file__), "test_distro_consumer.py"
            )
            # 依赖包的 site-packages 作为首参传入，被测 distro 置于
            # sys.path 最前——防系统环境已装同名 distro 干扰
            site = os.path.join(
                self.dependencies[self.tested_reference_str].package_folder,
                "lib", f"python{sys.version_info.major}.{sys.version_info.minor}",
                "site-packages",
            )
            self.run(
                f'{python_exe} "{test_script}" "{site}"', env="conanrun"
            )
