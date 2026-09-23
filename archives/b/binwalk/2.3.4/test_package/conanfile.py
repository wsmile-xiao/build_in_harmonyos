#!/usr/bin/env python3
"""test_package for binwalk 2.3.4 — smoke test (R34)."""
import os

from conan import ConanFile
from conan.errors import ConanException


class BinwalkTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Run test.sh which imports binwalk and runs --help
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        ret = self.run(f'"{bash}" test.sh', env="conanrun")
        if ret != 0:
            raise ConanException(f"test.sh failed with exit code {ret}")
