#!/usr/bin/env python3
"""Conan test_package — akms 0.3.0 (Alpine Kernel Module Support).

L1 official test: verifies the akms shell tool is packaged correctly.
The test script checks:
  - bin/akms exists and is executable
  - akms --version reports 0.3.0
  - akms --help exits 0
  - helper scripts akms-build/akms-runas are installed
"""
import os
from pathlib import Path

from conan import ConanFile


class AkmsTestConan(ConanFile):
    test_type = "explicit"

    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Locate the akms package root via Conan 2 dependencies API.
        pkg_root = None
        try:
            dep = self.dependencies.get("akms")
            if dep and dep.package_folder:
                pkg_root = Path(dep.package_folder)
        except (KeyError, AttributeError, TypeError) as e:
            self.output.warning(f"Could not get akms package_folder via dependencies API: {e}")

        test_script = Path(__file__).parent / "test_akms.sh"
        if pkg_root:
            os.environ["AKMS_PKG_ROOT"] = str(pkg_root)
        self.run(f'sh {test_script}')
