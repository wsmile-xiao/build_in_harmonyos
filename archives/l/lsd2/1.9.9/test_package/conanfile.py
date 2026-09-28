#!/usr/bin/env python3
"""test_package for lsd2 executable — runs the installed `lsd2` binary.

Consumer verification: invoke the installed binary the way a real user would,
with the upstream h1n1 example (rooted tree + date constraints), and check
that it produces a dating result (rate + tMRCA) with exit code 0.
"""
import os

from conan import ConanFile


class Lsd2TestConan(ConanFile):
    """test_package for lsd2 — runs test.sh which invokes the lsd2 binary."""
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