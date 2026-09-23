#!/usr/bin/env python3
"""Conan test_package for libgsasl-tools 2.2.4.

The tested package ships a single command line program, so the test runs it for
real (R34): the --version/--help contract, the mechanism inventory, a
deterministic SCRAM key derivation through `--mkpasswd`, and negative controls.
"""
import os

from conan import ConanFile


class LibgsaslToolsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS /system/bin/sh (mksh) cannot execute ELF binaries; use bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")