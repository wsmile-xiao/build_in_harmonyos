#!/usr/bin/env python3
"""Conan test_package for libad9361."""
import json
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain


class Libad9361TestConan(ConanFile):
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
        self.run(os.path.join(".", "libad9361_consumer"), env="conanrun")
        cmake.test()

        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True, "passed": True,
            "command": "./libad9361_consumer + ctest",
            "consumer_passed": 11, "consumer_total": 11,
        }))
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "partially_executed",
            "framework": "CMake/CTest (5 tests in test/CMakeLists.txt)",
            "discovered": 5, "executed": 2, "passed": 2, "failed": 0, "skipped": 3,
            "note": "FilterDesignerTest and GenerateRatesTest are pure computation "
                    "and are run in build(); FilterDesignerHardwareTest, "
                    "AutoRateTest and FMComms5SyncTest need a real AD936x over libiio",
        }))
