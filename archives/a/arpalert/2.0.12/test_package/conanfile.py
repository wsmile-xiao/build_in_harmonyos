#!/usr/bin/env python3
"""Conan test_package for arpalert 2.0.12 — runs test.sh which invokes the binary.

R34: This test substantively depends on the tested package by running
the arpalert binary with -h and -V flags via test.sh.
"""
import os

from conan import ConanFile


class ArpalertTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: Run test.sh which invokes the arpalert binary
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries, use bash
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
