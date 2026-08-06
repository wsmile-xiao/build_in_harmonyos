#!/usr/bin/env python3
"""Conan test_package — ccache 4.12.1

L1 smoke test: verifies that the ccache binary is installed and can report
its version. This is a consumer-perspective test (R34).
"""
import os

from conan import ConanFile


class CcacheTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: actually execute the ccache binary
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'{bash} -c "ccache --version"', env="conanrun")
