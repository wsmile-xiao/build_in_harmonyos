#!/usr/bin/env python3
"""Conan test_package for pyvolumio 0.1.5 — import + API smoke test.

Pure Python: always run the consumer test (do not gate on can_run).
CI L1e invokes `conan test -pr <host>` which may leave build=detected Linux
and make can_run() False, which would skip the test and false-fail R34.
"""
import os
import sys

from conan import ConanFile


class PyvolumioTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        python_exe = sys.executable
        test_script = os.path.join(os.path.dirname(__file__), "test_pyvolumio.py")
        self.run(f'{python_exe} "{test_script}"', env="conanrun")
