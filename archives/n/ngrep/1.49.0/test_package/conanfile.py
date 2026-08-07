#!/usr/bin/env python3
"""Conan test_package for ngrep — verifies the built binary works.

R34: Test exercises the actual package binary by running ngrep -V
via a bash-wrapped test.sh (pattern matches other OHOS executables).
"""
import os

from conan import ConanFile


class NgrepTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Use bash to wrap binary execution (pattern from aa3d, bash, etc.)
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
