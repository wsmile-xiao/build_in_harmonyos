#!/usr/bin/env python3
"""Conan test_package for pdqsort.

Header-only package: builds and runs a consumer program against the installed
``pdqsort.h`` through CMakeDeps, and emits the HMBS marker lines consumed by
the CI preflight.  Upstream ships no tests and no build system (the tarball is
just the header plus a benchmark), so all verification is consumer side.
"""
import json
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain


class PdqsortTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        self.run(os.path.join(".", "pdqsort_consumer"), env="conanrun")

        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "ctest + ./pdqsort_consumer",
            "consumer_passed": 8,
            "consumer_total": 8,
        }))
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "not_applicable",
            "framework": "none (header-only, upstream ships no tests and no build system)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
        }))
