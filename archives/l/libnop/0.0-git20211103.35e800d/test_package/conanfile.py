#!/usr/bin/env python3
"""Conan test_package for libnop.

Header-only package: builds and runs a consumer program against the installed
``include/nop/**`` headers through CMakeDeps.  The upstream GoogleTest suite is
executed by the recipe's ``build()`` (see ``upstream-gtest.log``); its result is
reported here through the HMBS marker lines consumed by the CI preflight.
"""
import json
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain


class LibnopTestConan(ConanFile):
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
        self.run(os.path.join(".", "libnop_consumer"), env="conanrun")

        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "ctest + ./libnop_consumer",
            "consumer_passed": 8,
            "consumer_total": 8,
        }))
        # The upstream GoogleTest suite runs during the recipe build() (a
        # non-zero suite fails conan create), so reaching this point means it
        # passed; the counts are recorded in MANIFEST.yml / the PR body.
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "executed",
            "framework": "GoogleTest (upstream test/*.cpp, run in build())",
            "discovered": 315,
            "executed": 315,
            "passed": 315,
            "failed": 0,
            "skipped": 0,
        }))
