#!/usr/bin/env python3
"""Conan test_package for console-common 0.7.92（house 模板，acme.sh 先例）。"""
import os
import shutil

from conan import ConanFile


class ConsoleCommonTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        pkg_folder = self.dependencies[self.tested_reference_str].package_folder
        script = os.path.join(self.source_folder, "test_console_common.sh")
        self.run(
            f'"{bash}" "{script}"',
            env="conanrun",
            cwd=pkg_folder,
        )
