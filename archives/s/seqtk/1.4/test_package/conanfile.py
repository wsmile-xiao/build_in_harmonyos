#!/usr/bin/env python3
"""Conan test package for seqtk 1.4."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration


class SeqtkTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"seqtk test supports Linux and OHOS only, got {self.settings.os}"
            )

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        script = os.path.join(self.recipe_folder, "test_seqtk.sh")
        shell = os.environ.get("CONFIG_SHELL") or "sh"
        binary = os.path.join(
            self.dependencies["seqtk"].package_folder,
            "bin",
            "seqtk",
        )
        if not os.path.isfile(binary):
            raise ConanInvalidConfiguration(
                f"seqtk binary not found in package: {binary}"
            )
        self.run(f'"{shell}" "{script}" "{binary}"', env="conanrun")
