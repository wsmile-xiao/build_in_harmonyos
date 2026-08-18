#!/usr/bin/env python3
"""test_package for eless — runs the eless script to verify it is installed and executable.

eless is a pure bash script tool. The test invokes `eless -V` to verify the
script is correctly installed and can report its version (R34: test must
substantially depend on the tested package).
"""
import os

from conan import ConanFile


class ElessTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # R34: test must substantively depend on the tested package.
        # Run `eless -V` which prints "Eless version v0.7".
        self.run(f"{bash} test.sh", env="conanrun")
