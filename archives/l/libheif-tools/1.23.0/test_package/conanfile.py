#!/usr/bin/env python3
"""Conan test_package for libheif-tools 1.23.0.

The tested package only ships command line binaries, so the test drives the
real heif-info over the upstream AVIF fixture (kept as base64 text, R02),
checks every installed tool's --version contract, and asserts the failure
mode for a missing input file (R34: the test must run the binaries).
"""
import os

from conan import ConanFile


class LibheifToolsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS /system/bin/sh (mksh) cannot execute ELF binaries; use bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")