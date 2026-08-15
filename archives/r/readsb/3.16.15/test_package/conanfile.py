#!/usr/bin/env python3
"""Conan test_package for readsb 3.16.15 — consumer smoke test.

Runs test_readsb.py (real test source file, satisfies L0c) against the
installed readsb binary, and compiles+runs the upstream CPR decoder unit
tests (cprtests.c from the upstream dev branch, bundled with cpr.h/cpr.c).
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class ReadsbTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["readsb"].package_folder
        rbin = os.path.join(pkg, "bin", "readsb")
        test_script = os.path.join(os.path.dirname(__file__), "test_readsb.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_readsb.py missing: {test_script}")
        if not os.path.isfile(rbin):
            raise ConanException(f"readsb binary missing: {rbin}")
        self.run(f'python3 "{test_script}" "{rbin}"')

        # Upstream CPR decoder unit tests (cprtests.c from dev branch)
        tp = os.path.dirname(__file__)
        for f in ("cprtests.c", "cpr.h", "cpr.c"):
            if not os.path.isfile(os.path.join(tp, f)):
                raise ConanException(f"upstream test file missing: {f}")
        exe = os.path.join(self.build_folder, "cprtests")
        self.run(
            f'clang -o "{exe}" "{tp}/cprtests.c" "{tp}/cpr.c" -lm'
        )
        self.run(f'"{exe}"')
