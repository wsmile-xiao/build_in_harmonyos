#!/usr/bin/env python3
"""test_package for cargo-nextest — runs test.sh which invokes the binary."""
import os

from conan import ConanFile


class CargoNextestTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution.
        # On OHOS, CONFIG_SHELL is set by the conan profile to /data/service/hnp/bin/bash.
        # On Linux, fall back to standard bash.
        bash = os.environ.get("CONFIG_SHELL", "bash")
        self.run(f"{bash} test.sh", env="conanrun")
