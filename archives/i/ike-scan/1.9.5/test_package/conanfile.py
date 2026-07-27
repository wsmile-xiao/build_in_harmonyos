#!/usr/bin/env python3
"""Test package for ike-scan 1.9.5."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import copy, load


class IkeScanTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def export_sources(self):
        copy(self, "test_ike_scan.sh", self.recipe_folder, self.export_sources_folder)

    def test(self):
        if can_run(self):
            script = os.path.join(self.source_folder, "test_ike_scan.sh")
            self.run(f'sh "{script}"', env="conanrun")
            output = load(self, os.path.join(self.build_folder, "ike-scan-version.txt"))
            if "ike-scan" not in output.lower():
                raise Exception(f"unexpected ike-scan version output: {output!r}")
