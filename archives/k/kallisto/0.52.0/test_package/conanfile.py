#!/usr/bin/env python3
"""Conan test_package for kallisto 0.52.0 — consumer smoke test.

Runs test_kallisto.py (real test source file, satisfies L0c) against the
installed kallisto binary: version assertion + real index+quant on bundled
upstream unit_tests input data (share/kallisto/unit_tests/input).
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class KallistoTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["kallisto"].package_folder
        kbin = os.path.join(pkg, "bin", "kallisto")
        data_dir = os.path.join(pkg, "share", "kallisto", "unit_tests", "input")
        test_script = os.path.join(os.path.dirname(__file__), "test_kallisto.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_kallisto.py missing: {test_script}")
        if not os.path.isdir(data_dir):
            raise ConanException(f"upstream test data missing: {data_dir}")
        self.run(f'python3 "{test_script}" "{kbin}" "{data_dir}"')
