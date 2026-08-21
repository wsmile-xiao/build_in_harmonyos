#!/usr/bin/env python3
"""test_package for epstool — runs the epstool binary to verify it works.

R34: test must actually invoke the tested package's binary (not a stub).
This test runs epstool --help and checks for expected output.
"""
import os

from conan import ConanFile


class EpstoolTestConan(ConanFile):
    """test_package for executable packages — runs test.sh which invokes the binary."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
