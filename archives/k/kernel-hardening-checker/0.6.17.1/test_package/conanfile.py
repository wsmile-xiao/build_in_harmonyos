#!/usr/bin/env python3
"""Conan test_package for kernel-hardening-checker 0.6.17.1.

Runs (with the conanrun environment, PYTHONPATH from package_info):
  * upstream engine unit tests (14 cases) against the installed package
  * consumer smoke tests: import/__version__, CLI wrapper --version,
    -p, -c with plain/gzipped/shipped-sample Kconfig, error path
"""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class KernelHardeningCheckerTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            python_exe = sys.executable
            test_script = os.path.join(os.path.dirname(__file__), "test_khc.py")
            self.run(f'{python_exe} "{test_script}"', env="conanrun")
