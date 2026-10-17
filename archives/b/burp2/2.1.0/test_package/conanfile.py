#!/usr/bin/env python3
"""Conan test_package — burp2 executable smoke + functional tests.

Runs test.sh which exercises the installed burp/vss_strip/burp_ca binaries.
"""
import os

from conan import ConanFile


class Burp2TestConan(ConanFile):
    """test_package for the burp2 executable."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use the build shell explicitly to wrap binary execution.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
