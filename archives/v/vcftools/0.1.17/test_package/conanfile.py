#!/usr/bin/env python3
"""Consumer tests for the packaged VCFtools command-line tools."""
import os

from conan import ConanFile
from conan.tools.build import can_run


class VcftoolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
            self.run(f'"{bash}" test.sh', env="conanrun")
