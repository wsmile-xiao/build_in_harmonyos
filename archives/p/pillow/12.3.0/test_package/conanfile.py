#!/usr/bin/env python3
"""Consumer test for the installed pillow/12.3.0 package."""
import os
import sys

from conan import ConanFile


class PillowTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dependency = self.dependencies["pillow"]
        site_packages = os.path.join(
            dependency.package_folder, "lib", "python3.12", "site-packages"
        )
        test_script = os.path.join(os.path.dirname(__file__), "test_pillow.py")
        harmonyos_script = os.path.join(os.path.dirname(__file__), "test_harmonyos_runtime.py")
        self.run(
            f'"{sys.executable}" -I "{test_script}" "{site_packages}"',
            env="conanrun",
        )
        self.run(
            f'"{sys.executable}" -I "{harmonyos_script}" "{site_packages}" '
            f'"{self.settings.os}" "{self.settings.arch}"',
            env="conanrun",
        )
