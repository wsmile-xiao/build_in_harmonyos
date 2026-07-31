#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/{letter}/ansiweather/{version}/test_package/conanfile.py
"""
from conan import ConanFile


class AnsiweatherTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # CLI smoke test: run test_ansiweather.sh via conanrun environment
        self.run("bash test_ansiweather.sh ansiweather", env="conanrun")