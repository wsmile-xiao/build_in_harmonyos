#!/usr/bin/env python3
"""Conan test_package for darkice 1.6 (live audio streamer)."""
import os

from conan import ConanFile
from conan.tools.build import can_run


class DarkiceTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
