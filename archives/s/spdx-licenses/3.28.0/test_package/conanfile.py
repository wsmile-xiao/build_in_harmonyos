#!/usr/bin/env python3
"""test_package for spdx-licenses 3.28.0.

Smoke-test consumer verification:
  1. Confirm licenseListVersion == 3.28.0
  2. Count licenses == 727, deprecated == 32
  3. Count exceptions == 84, deprecated exceptions == 1
  4. Query MIT, Apache-2.0, BSD-3-Clause, GPL-2.0-only must succeed
  5. Query NOT-A-REAL-SPDX-ID must fail
  6. Output fixed JSON summary for exact comparison
"""
import os
import json

from conan import ConanFile


class SpdxLicensesTestConan(ConanFile):
    settings = None

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        # Data-only package, no cmake layout needed
        pass

    def build(self):
        # No compilation needed
        pass

    def test(self):
        # Locate the data from the dependency's package_folder
        dep = self.dependencies["spdx-licenses"]
        res_dir = os.path.join(dep.package_folder, "res")

        # Call the standalone test script via self.run() (L0d gate requirement)
        self.run(f"python3 test_spdx.py \"{res_dir}\"", cwd=self.source_folder, env="conanrun")
