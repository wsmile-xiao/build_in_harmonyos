#!/usr/bin/env python3
"""Conan test_package for libdisplay-info-tools 0.3.0.

The tested package only ships a command line binary, so the test decodes the
upstream EDID fixture (kept as base64 text, R02) and executes the real
di-edid-decode over it, asserting on the decoded report and on its behaviour
for an empty input (R34: the test must actually run the binary).
"""
import os

from conan import ConanFile


class LibdisplayInfoToolsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS /system/bin/sh (mksh) cannot execute ELF binaries; use bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")