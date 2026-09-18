#!/usr/bin/env python3
"""Conan test_package for pwquality 1.4.5 — runs the R34 consumer check.

Compiles a C program against the packaged ``pwquality.h`` + ``libpwquality.so``
and runs it (real API usage), verifies the ``pwquality.pc`` pkg-config contract,
and executes the packaged ``pwscore`` / ``pwmake`` tools.
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            raise ConanException("cannot run on this platform")
        pkg = self.dependencies["pwquality"].package_folder
        if not os.path.isfile(os.path.join(pkg, "include", "pwquality.h")):
            raise ConanException(f"pwquality.h missing under {pkg}/include")
        test_script = os.path.join(os.path.dirname(__file__), "test_pwquality.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_pwquality.py missing: {test_script}")
        self.run(f'{sys.executable} "{test_script}" "{pkg}"', env="conanrun")
