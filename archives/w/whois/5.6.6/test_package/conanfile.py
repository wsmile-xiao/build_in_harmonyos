#!/usr/bin/env python3
"""Conan test_package — whois 5.6.6

Tests the whois binary by running --version via test.sh.
R34: Test must actually exercise the packaged binary.
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class WhoisTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        whois_bin = os.path.join(self.dependencies["whois"].package_folder, "bin", "whois")
        test_script = os.path.join(self.source_folder, "test.sh")
        bash = os.environ.get("CONFIG_SHELL", "bash")
        self.run(f'WHOIS_BIN="{whois_bin}" {bash} "{test_script}"', env="conanrun")
