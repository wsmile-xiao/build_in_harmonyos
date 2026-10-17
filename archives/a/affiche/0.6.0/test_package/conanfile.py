#!/usr/bin/env python3
"""Conan test_package for affiche 0.6.0."""
import os

from conan import ConanFile
from conan.tools.build import can_run


class AfficheTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["affiche"].package_folder
        bundle = os.path.join(pkg, "share", "GNUstep", "Affiche.app")
        script = os.path.join(self.source_folder, "test_bundle.py")
        if not can_run(self):
            self.output.info(
                f"cross-building: bundle smoke test recorded for {bundle}"
            )
            return
        self.run(f'python3 "{script}" "{bundle}"', env="conanrun")
