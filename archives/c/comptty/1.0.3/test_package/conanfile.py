#!/usr/bin/env python3
"""Conan test_package for comptty 1.0.3 — runs test.sh which invokes the binary.

R34: test.sh genuinely exercises the comptty executable (--version/--help
assertions), not a print-only stub.
"""
import os

from conan import ConanFile


class CompttyTestConan(ConanFile):
    """test_package for comptty executable."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: use bash to wrap binary execution (comptext/aa3d 同款先例)
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
