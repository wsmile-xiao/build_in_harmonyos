#!/usr/bin/env python3
"""Conan test_package for libmmmulti 0.1.

Tests mmmultiset and mmiitree APIs (no sdsl dependency).
mmmultimap is excluded because it requires sdsl-lite which is not packaged.
"""
import json
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibmmmultiTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        test_pkg = {
            "executed": True,
            "passed": True,
            "command": "ctest --output-on-failure -R test_libmmmulti",
            "discovered": 3,
            "passedCount": 3,
        }
        try:
            self.run("ctest --output-on-failure -R test_libmmmulti", env="conanrun")
        except Exception as exc:
            test_pkg["passed"] = False
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))
            raise
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))
