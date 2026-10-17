#!/usr/bin/env python3
"""Conan test_package for aaphoto (Auto Adjust Photo CLI).

aaphoto is a command-line tool, so the L1 test runs a real end-to-end
processing job (R34): generate a tiny BMP image, run `aaphoto` on it and
assert that the corrected output image is produced.  Also verifies that the
`--version` switch works.
"""
import os

from conan import ConanFile


class AaphotoTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS /system/bin/sh (mksh) cannot execute ELF binaries; use bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
