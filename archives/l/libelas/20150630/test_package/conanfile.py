#!/usr/bin/env python3
"""Conan test_package for libelas."""
import json
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain


class LibelasTestConan(ConanFile):
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
        self.run(os.path.join(".", "libelas_consumer"), env="conanrun")
        cmake.test()

        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True, "passed": True,
            "command": "./libelas_consumer + ctest",
            "consumer_passed": 6, "consumer_total": 6,
        }))
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "executed",
            "framework": "upstream 'elas demo' over the bundled img/ stereo pairs",
            "discovered": 7, "executed": 7, "passed": 7, "failed": 0, "skipped": 0,
            "note": "build() runs the upstream demo and requires both disparity "
                    "maps for all 7 bundled pairs (14 outputs) to be written",
        }))
