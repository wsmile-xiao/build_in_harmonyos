#!/usr/bin/env python3
"""Conan test_package for yx (YAML Data Extraction Tool CLI).

yx is a command-line tool, so the L1 test runs the installed `yx` binary
end-to-end (R34): it feeds YAML documents on stdin / via -f and asserts the
extracted keys, nested scalar values and sequence indices, plus the failure
path for an unknown key.
"""
import os

from conan import ConanFile


class YxTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS /system/bin/sh (mksh) cannot execute ELF binaries; use bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
