#!/usr/bin/env python3
"""Conan test_package for comptext 1.0.1 — runs test.sh which invokes the binary.

R34: test.sh genuinely exercises the comptext executable (--version/--help
assertions), not a print-only stub.
"""
import os

from conan import ConanFile


class ComptextTestConan(ConanFile):
    """test_package for comptext executable."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: use bash to wrap binary execution (aa3d 同款先例)
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
