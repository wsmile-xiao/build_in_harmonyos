#!/usr/bin/env python3
"""Consumer test for the packaged multipledispatch API."""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class MultipledispatchTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            script = os.path.join(self.source_folder, "test_multipledispatch.py")
            self.run(f'"{sys.executable}" "{script}"', env="conanrun")
