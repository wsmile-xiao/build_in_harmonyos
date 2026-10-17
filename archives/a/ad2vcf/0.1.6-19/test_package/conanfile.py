#!/usr/bin/env python3
"""Consumer smoke test for ad2vcf 0.1.6-19."""

import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class Ad2vcfTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "test_ad2vcf.py"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("Skipping ad2vcf runtime smoke because target binaries cannot run")
            return
        package_folder = self.dependencies["ad2vcf"].package_folder
        script = os.path.join(self.source_folder, "test_ad2vcf.py")
        self.run(f'"{sys.executable}" "{script}" "{package_folder}"', cwd=self.build_folder, env="conanrun")
