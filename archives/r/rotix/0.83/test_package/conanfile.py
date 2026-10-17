#!/usr/bin/env python3
"""test_package for the rotix executable — runs the installed binary as a consumer.

Verifies that a consumer can invoke the packaged ``rotix`` binary end to end:
ROT13 forward/roundtrip, identity wrap-around, left rotation, case handling,
stdin input, argument validation and the ``-a`` all-rotations mode.
"""
import os

from conan import ConanFile


class RotixTestConan(ConanFile):
    """test_package for rotix executable — runs test.sh against the installed binary."""
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
