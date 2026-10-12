#!/usr/bin/env python3
"""Functional package test for Redex."""

import os
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv


class RedexTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    exports_sources = "test_redex_package.py", "harmony_tests/*", "HARMONY_TESTS.yml"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        VirtualRunEnv(self).generate()

    def test(self):
        dependency = self.dependencies["redex"]
        binary = os.path.join(dependency.package_folder, "bin", "redex-all")
        driver = os.path.join(dependency.package_folder, "bin", "redex.py")
        missing = [path for path in (binary, driver) if not os.path.isfile(path)]
        if missing:
            raise ConanInvalidConfiguration(
                "Redex package is missing required artifacts: " + ", ".join(missing)
            )

        if not can_run(self):
            return

        test_script = os.path.join(self.source_folder, "test_redex_package.py")
        self.run(
            " ".join(
                [
                    f'"{sys.executable}"',
                    f'"{test_script}"',
                    f'"{binary}"',
                    f'"{driver}"',
                ]
            ),
            env="conanrun",
        )
        if self.settings.os == "OHOS":
            harmony_script = os.path.join(
                self.source_folder, "harmony_tests", "test_signed_hmdfs.py"
            )
            self.run(
                f'"{sys.executable}" "{harmony_script}" "{binary}"',
                env="conanrun",
            )
