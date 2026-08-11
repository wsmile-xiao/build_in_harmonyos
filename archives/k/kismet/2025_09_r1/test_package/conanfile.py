#!/usr/bin/env python3
import sys
from pathlib import Path

from conan import ConanFile
from conan.tools.build import can_run


class KismetTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        test_script = Path(self.source_folder) / "test_cli.py"
        self.run(f'"{sys.executable}" "{test_script}"', env="conanrun")
