#!/usr/bin/env python3
"""Conan test_package for autoenv 0.4.0."""
import os
import tempfile

from conan import ConanFile
from conan.tools.build import can_run


class AutoenvTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        dep = self.dependencies["autoenv"]
        activate = os.path.join(dep.package_folder, "res", "autoenv", "activate.sh")
        if not os.path.isfile(activate):
            raise Exception(f"activate.sh not found: {activate}")

        with tempfile.TemporaryDirectory(prefix="autoenv-test-") as tmpdir:
            script = os.path.join(self.source_folder, "test.sh")
            self.run(
                f'cd "{tmpdir}" && AUTOENV_ACTIVATE="{activate}" bash "{script}"',
                env="conanrun",
            )
