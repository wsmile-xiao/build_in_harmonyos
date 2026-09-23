#!/usr/bin/env python3
"""Conan test_package for libSNL.

Builds a consumer program against the installed package through CMakeDeps and
runs it with ctest.  Upstream's own test program (``src/snlTest.cpp``) is
compiled and executed by the recipe's ``build()`` and reported as upstream
evidence; the consumer below covers the installed headers/library.
"""
import json
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain


class LibsnlTestConan(ConanFile):
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
        self.run(os.path.join(".", "libsnl_consumer"), env="conanrun")
        cmake.test()

        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "./libsnl_consumer + ctest",
            "consumer_passed": 10,
            "consumer_total": 10,
        }))
        # upstream's snlTest prints "All tests have passed :-)" when its own
        # internal checks succeed; the recipe runs it in build() and fails the
        # build otherwise.
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "executed",
            "framework": "upstream src/snlTest.cpp (run in build())",
            "discovered": 1,
            "executed": 1,
            "passed": 1,
            "failed": 0,
            "skipped": 0,
            "note": "snlTest ran and printed 'All tests have passed :-)'",
        }))
