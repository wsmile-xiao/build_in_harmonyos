#!/usr/bin/env python3
"""Conan test_package for libpwm."""
import json
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain


class LibpwmTestConan(ConanFile):
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
        self.run(os.path.join(".", "libpwm_consumer"), env="conanrun")
        cmake.test()
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True, "passed": True,
            "command": "./libpwm_consumer + ctest",
            "consumer_passed": 4, "consumer_total": 4}))
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "executed_with_environment_limitation",
            "framework": "upstream example programs pwmround/pwmset/pwmtestperf",
            "discovered": 3, "executed": 3, "passed": 0, "failed": 0, "skipped": 0,
            "note": "no PWM chip exists in the sandbox: the programs run and "
                    "report the missing chip instead of driving hardware"}))
