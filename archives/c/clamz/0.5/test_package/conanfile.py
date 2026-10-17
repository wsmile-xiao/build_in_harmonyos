#!/usr/bin/env python3
"""Conan test_package for clamz — verifies the built CLI works.

clamz is a command-line application; the L1 test runs the binary with
--help / --version / no-args / an invalid option and asserts the expected
behavior (exit code and output) via test.sh.
"""
import os

from conan import ConanFile
from conan.tools.env import VirtualRunEnv


class ClamzTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) may not execute ELF binaries reliably.
        # Use bash to wrap binary execution.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
