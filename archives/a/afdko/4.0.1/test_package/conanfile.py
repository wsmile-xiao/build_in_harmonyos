#!/usr/bin/env python3
"""Conan consumer test for afdko 4.0.1."""

import os
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class AfdkoTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def configure(self):
        self.settings.rm_safe("os.version")

    def test(self):
        if not can_run(self):
            return
        bin_dir = os.path.join(self.dependencies[self.tested_reference_str].package_folder, "bin")
        test_script = os.path.join(self.source_folder, "test_afdko.sh")
        # R34: real invocation of afdko binaries via test script
        self.run("/bin/sh " + test_script + " " + bin_dir, env="conanrun")
