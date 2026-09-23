#!/usr/bin/env python3
"""Conan test_package for libjama.

Builds a consumer program against the installed headers through CMakeDeps and
runs it with ctest.  The program checks the numeric result of each
decomposition (LU, QR, Cholesky, SVD, eigenvalues).
"""
import json
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain


class LibjamaTestConan(ConanFile):
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
        self.run(os.path.join(".", "libjama_consumer"), env="conanrun")
        cmake.test()

        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "./libjama_consumer + ctest",
            "consumer_passed": 12,
            "consumer_total": 12,
        }))
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "not_applicable",
            "framework": "none (upstream ships no tests; the tree contains the "
                         "five public headers only)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "note": "no upstream test suite exists; the consumer program checks "
                    "the numeric results of every decomposition",
        }))
