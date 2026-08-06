#!/usr/bin/env python3
"""test_package conanfile for ffuf — smoke tests the ffuf binary."""
import os
import shutil

from conan import ConanFile


class FfufTestConan(ConanFile):
    """test_package for ffuf executable — runs test.sh which invokes the binary."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "bash"
        self.run(f"{bash} test.sh", env="conanrun")
