#!/usr/bin/env python3
"""Conan test_package for libdv-tools 1.0.0.

The tested package ships three command line programs, so the test runs them
for real (R34): the popt based --version/--help contract, the regression guard
for the "built without HAVE_LIBPOPT" failure mode (the tools used to die with
SIGSEGV instead of printing usage), and negative controls for unknown options
and a missing input pattern.
"""
import os

from conan import ConanFile


class LibdvToolsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS /system/bin/sh (mksh) cannot execute ELF binaries; use bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")