#!/usr/bin/env python3
"""Conan test_package — alex 3.5.4.2 (Haskell lexer generator).

L1 official test: verifies the alex binary is packaged and functional.
The test script checks:
  - alex binary exists
  - alex --version reports 3.5.4.2
  - alex generates a lexer from a minimal .x spec (functional, --template
    pointing at the packaged templates)

Note: alex --help is NOT asserted — on OHOS the GHC RTS intermittently
hangs in sigsuspend when alex prints the help text and exits.
"""
import os
from pathlib import Path

from conan import ConanFile


class AlexTestConan(ConanFile):
    test_type = "explicit"

    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Locate the alex package root via Conan 2 dependencies API.
        pkg_root = None
        try:
            dep = self.dependencies.get("alex")
            if dep and dep.package_folder:
                pkg_root = Path(dep.package_folder)
        except (KeyError, AttributeError, TypeError) as e:
            self.output.warning(f"Could not get alex package_folder via dependencies API: {e}")

        test_script = Path(__file__).parent / "test_alex.sh"
        if pkg_root:
            os.environ["ALEX_PKG_ROOT"] = str(pkg_root)
        self.run(f'sh {test_script}')
