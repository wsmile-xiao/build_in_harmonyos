#!/usr/bin/env python3
"""Conan test_package for sha3sum 1.2.5 — L1 smoke test.

sha3sum is a command-line tool; we verify it runs and produces
correct SHA-3-224 output for empty input.
"""
import os

from conan import ConanFile


class Sha3SumTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bindir = os.path.join(self.dependencies["sha3sum"].package_folder, "bin")
        sha3sum = os.path.join(bindir, "sha3sum")
        libkeccak = self.dependencies["libkeccak"]
        libdir = os.path.join(libkeccak.package_folder, libkeccak.cpp_info.libdirs[0])

        # Smoke test: sha3sum on empty input must produce correct SHA-3-224 hash.
        # SHA-3-224("") = 6b4e03423667dbb73b6e15454f0eb1abd4597f9a1b078e3f5b5a6bc7
        self.run(
            f'printf "" | {sha3sum} | grep -q "6b4e03423667dbb73b6e15454f0eb1abd4597f9a1b078e3f5b5a6bc7"',
            env=[f"LD_LIBRARY_PATH={libdir}"],
        )
        self.output.info("sha3sum smoke test PASSED")
