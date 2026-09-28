#!/usr/bin/env python3
"""test_package for xcmsdb 1.0.7 - consumer check of the installed binary."""
import os

from conan import ConanFile


class XcmsdbTestConan(ConanFile):
    """Runs the installed xcmsdb binary through headless-safe code paths."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(bash + " test.sh", env="conanrun")
