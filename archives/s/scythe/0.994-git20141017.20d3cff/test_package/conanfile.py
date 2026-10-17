#!/usr/bin/env python3
"""Consumer tests for the scythe executable."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class ScytheTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", cwd=self.source_folder, env="conanrun")
