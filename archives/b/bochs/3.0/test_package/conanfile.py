#!/usr/bin/env python3
"""Conan test package - Bochs 3.0 headless BIOS smoke test."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class BochsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: command tests cannot run")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        for script_name in ("unit_test.sh", "test.sh"):
            script = os.path.join(self.source_folder, script_name)
            self.run(f'"{bash}" "{script}"', env="conanrun")
