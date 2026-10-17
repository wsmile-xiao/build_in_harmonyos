#!/usr/bin/env python3
"""Conan test_package for optipng — PNG image optimizer CLI.

optipng is a command-line tool, so the L1 test runs a real end-to-end
optimization job (R34): generate a tiny PNG image, run `optipng` on it
and verify the output is produced. Also verifies the `--version` switch.
"""
import os

from conan import ConanFile


class OptipngTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS /system/bin/sh (mksh) cannot execute ELF binaries; use bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
