#!/usr/bin/env python3
"""Conan test_package for aconf-mod-network."""
import os
import shutil

from conan import ConanFile


class AconfModNetworkTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["aconf-mod-network"].package_folder
        shell = os.environ.get("CONFIG_SHELL") or shutil.which("sh") or "/bin/sh"
        script = os.path.join(self.source_folder, "test_network.sh")
        self.run(f'"{shell}" "{script}" "{pkg_folder}"', env="conanrun")
