#!/usr/bin/env python3
"""test_package for es-shell — CLI tool smoke test (R34: must run the binary)."""
import os

from conan import ConanFile


class EsshellTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "bash")
        self.run(f"{bash} test.sh", env="conanrun")
