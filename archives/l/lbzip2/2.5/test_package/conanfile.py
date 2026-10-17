#!/usr/bin/env python3
"""Conan test_package — lbzip2 2.5.

R34/L0c compliant: exports a real test source (test.sh) that runs the
INSTALLED lbzip2/lbunzip2 binaries (compress -> decompress -> cmp) and
fails when behavior is wrong. `test()` executes it under bash.
"""
import os

from conan import ConanFile


class Lbzip2TestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    # L0c: committed test source inside test_package/ (up to depth 2)
    exports_sources = "test.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) may not be reliable for ELF executions;
        # use bash (same pattern as aa3d test_package).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")