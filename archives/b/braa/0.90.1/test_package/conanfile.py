#!/usr/bin/env python3
"""Conan consumer test for braa — runs test.sh which executes the packaged
binary and asserts real behavior (banner/usage, argument validation, a real
SNMP GET over UDP to 127.0.0.1)."""
import os

from conan import ConanFile


class BraaTestConan(ConanFile):
    """test_package for braa executable — runs test.sh which exercises the binary."""
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
