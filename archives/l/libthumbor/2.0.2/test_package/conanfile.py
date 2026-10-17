#!/usr/bin/env python3
"""Consumer check for the installed libthumbor package."""

import os
import sys

from conan import ConanFile


class LibthumborTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        script = os.path.join(self.source_folder, "test_libthumbor.py")
        self.run(f'"{sys.executable}" "{script}"', env="conanrun")
