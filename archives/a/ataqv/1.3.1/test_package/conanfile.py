#!/usr/bin/env python3
"""Conan test_package for ataqv 1.3.1.

Tests the ataqv CLI binary by running `ataqv --version`.
This satisfies R34: test must execute the package's binary.
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class AtaqvTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        ataqv_bin = os.path.join(self.dependencies["ataqv"].cpp_info.bindirs[0], "ataqv")
        bash = os.environ.get("CONFIG_SHELL", "bash")
        self.run(f'{bash} "{os.path.join(self.source_folder, "test_ataqv.sh")}" "{ataqv_bin}"', env="conanrun")
