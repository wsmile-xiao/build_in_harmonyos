#!/usr/bin/env python3
"""Consumer test recipe for duc."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class DucTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    exports_sources = "test.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            self.run("duc --version", env="conanrun")
            script = os.path.join(self.source_folder, "test.sh")
            self.run(f"sh {script}", env="conanrun")
