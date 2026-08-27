#!/usr/bin/env python3
"""test_package for s6-dns — runs test.sh which verifies binaries.
Uses self.run() (L0d requirement). Test genuinely depends on the package
because it executes binaries from the package's bin/ directory."""
import os

from conan import ConanFile


class S6DnsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "bash")
        self.run(f"{bash} test.sh", env="conanrun")
