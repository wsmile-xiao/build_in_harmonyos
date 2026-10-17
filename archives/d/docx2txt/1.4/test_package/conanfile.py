#!/usr/bin/env python3
"""Conan test package — docx2txt 1.4 functional conversion"""

import os

from conan import ConanFile
from conan.tools.build import can_run


class Docx2txtTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
            self.run(f'"{bash}" "{os.path.join(self.source_folder, "test.sh")}"', env="conanrun")
