#!/usr/bin/env python3
"""Consumer test for cpio: create and extract a real archive."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class CpioTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("cross: cpio archive test deferred to target validation")
            return
        cpio = os.path.join(self.dependencies["cpio"].package_folder, "bin", "cpio")
        self.run(f'"{cpio}" --version', env="conanrun")
        test_script = os.path.join(self.source_folder, "test.sh")
        self.run(f'/system/bin/sh "{test_script}"', env="conanrun")
