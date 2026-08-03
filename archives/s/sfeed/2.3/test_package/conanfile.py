#!/usr/bin/env python3
"""Conan test package for sfeed 2.3."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration


class SfeedTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"sfeed test supports Linux and OHOS only, got {self.settings.os}"
            )

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        script = os.path.join(self.recipe_folder, "test_sfeed.sh")
        bin_dir = os.path.join(
            self.dependencies["sfeed"].package_folder,
            "bin",
        )
        if not os.path.isdir(bin_dir):
            raise ConanInvalidConfiguration(f"sfeed bin directory not found: {bin_dir}")
        shell = os.environ.get("CONFIG_SHELL") or "sh"
        self.run(f'"{shell}" "{script}" "{bin_dir}"', env="conanrun")
