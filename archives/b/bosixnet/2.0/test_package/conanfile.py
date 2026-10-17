#!/usr/bin/env python3
"""Conan test_package for bosixnet 2.0 — smoke test the shipped binary.

Runs `bosixnet_webui --version` and requires a zero exit code (the binary
prints the version banner and exits 0). This exercises the real packaged
binary as required by R34.
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class BosixnetTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        bin_path = os.path.join(self.dependencies["bosixnet"].package_folder,
                                "bin", "bosixnet_webui")
        self.run(f'"{bin_path}" --version', env="conanrun")