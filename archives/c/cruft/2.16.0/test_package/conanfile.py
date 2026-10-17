#!/usr/bin/env python3
"""Conan test_package for cruft 2.16.0.

Verifies that the Conan-packaged cruft can be imported, its CLI is
available, and its core create/check/diff flow works on the target.
"""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class CruftTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            python_exe = sys.executable

            # L1: import test
            self.run(
                f'"{python_exe}" -c "import cruft; '
                f"print('cruft version:', cruft.__version__)\"",
                env="conanrun",
            )

            # L2: CLI smoke test
            self.run("cruft --help", env="conanrun")

            # L4: functional test (create / check / diff)
            test_script = os.path.join(os.path.dirname(__file__), "test.py")
            self.run(f'"{python_exe}" "{test_script}"', env="conanrun")
