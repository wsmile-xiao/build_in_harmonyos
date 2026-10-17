#!/usr/bin/env python3
"""Consumer test for the packaged Adapt intent parser."""

import os
import sys

from conan import ConanFile


class AdaptTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        test_script = os.path.join(self.source_folder, "test_adapt.py")
        # VirtualRunEnv consumes the PYTHONPATH exported by adapt's package_info().
        # six remains an external runtime dependency and is not hidden here.
        self.run(f'"{sys.executable}" "{test_script}"', env="conanrun")
