#!/usr/bin/env python3
"""test_package for magicrescue 1.1.10 (CLI tool) — runs test.sh.

Consumer verification: invokes the installed `magicrescue` binary the way a
real user would — recover a gzip file from a disk-image blob using the shipped
`gzip` recipe, then verify the recovered payload content.
"""
import os

from conan import ConanFile


class MagicrescueTestConan(ConanFile):
    """test_package for the magicrescue executable — runs test.sh which invokes the binary."""
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
