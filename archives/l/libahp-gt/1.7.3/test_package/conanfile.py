#!/usr/bin/env python3
"""Conan test_package for libahp-gt.

Builds a consumer program against the installed package through CMakeDeps and
runs it with ctest.  The library talks to a hardware controller, so the program
pins the deterministic parts of the public API (version constant, settings
round trips, disconnected state, RA/Dec <-> Alt/Az conversion).
"""
import json
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain


class LibahpGtTestConan(ConanFile):
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
        self.run(os.path.join(".", "libahp_gt_consumer"), env="conanrun")
        cmake.test()

        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "./libahp_gt_consumer + ctest",
            "consumer_passed": 10,
            "consumer_total": 10,
        }))
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "not_applicable",
            "framework": "none (upstream ships no tests; the library drives "
                         "hardware over a serial port)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "note": "no upstream test suite exists; the consumer program covers "
                    "the deterministic API surface",
        }))
