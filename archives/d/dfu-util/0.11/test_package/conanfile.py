#!/usr/bin/env python3
"""Test package for dfu-util 0.11 — Conan L1 smoke test."""
import os

from conan import ConanFile
from conan.tools.build import can_run


class DfuUtilTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            script = os.path.join(self.source_folder, "test.sh")
            if str(self.settings.os) == "OHOS":
                bash = "/data/service/hnp/bin/bash"
            else:
                bash = "/bin/bash"
            self.run(f'{bash} "{script}"', env="conanrun")