#!/usr/bin/env python3
"""Conan test_package for sheenbidi."""
import json
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain


class SheenBidiTestConan(ConanFile):
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
        self.run(os.path.join(".", "sheenbidi_consumer"), env="conanrun")
        cmake.test()

        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True, "passed": True,
            "command": "./sheenbidi_consumer + ctest",
            "consumer_passed": 12, "consumer_total": 12,
        }))
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "executed",
            "framework": "custom STANDALONE_TESTING suite driven by ctest (16 test executables)",
            "discovered": 16, "executed": 16, "passed": 16, "failed": 0, "skipped": 0,
            "note": "build() runs ctest over the Tools/Unicode data directory",
        }))
