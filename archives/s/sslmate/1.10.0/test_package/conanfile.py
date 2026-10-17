#!/usr/bin/env python3
"""test_package for sslmate — runs test.sh which exercises the sslmate binary."""
import os

from conan import ConanFile


class SslmateTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # conanrun env puts the package's bin/ on PATH, so `sslmate` resolves.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
