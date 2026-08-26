#!/usr/bin/env python3
"""Conan test_package for vmdktool 1.4.

Runs test_vmdktool.sh which invokes the vmdktool binary
to verify --version output. R34: genuinely exercises the
tested package's binary.
"""
import os

from conan import ConanFile


class VmdktoolTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: use bash to wrap binary execution reliably
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test_vmdktool.sh", env="conanrun")
