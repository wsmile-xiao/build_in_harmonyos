#!/usr/bin/env python3
"""Consumer test for Timewarrior 1.9.1."""

import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class TimewarriorTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            binary = os.path.join(
                self.dependencies["timewarrior"].package_folder,
                "bin",
                "timew",
            )
            script = os.path.join(self.source_folder, "test.sh")
            bash = (
                os.environ.get("CONFIG_SHELL")
                or shutil.which("bash")
                or "/data/service/hnp/bin/bash"
            )
            self.run(f'"{bash}" "{script}" "{binary}"', env="conanrun")
