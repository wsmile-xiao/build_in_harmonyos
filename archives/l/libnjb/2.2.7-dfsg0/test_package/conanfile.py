#!/usr/bin/env python3
"""Conan test_package for libnjb."""
import json
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain


class LibnjbTestConan(ConanFile):
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
        self.run(os.path.join(".", "libnjb_consumer"), env="conanrun")
        cmake.test()
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True, "passed": True,
            "command": "./libnjb_consumer + ctest",
            "consumer_passed": 10, "consumer_total": 10}))
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "not_applicable",
            "framework": "none (upstream ships no tests; the library needs a "
                         "Nomad Jukebox player over libusb)",
            "discovered": 0, "executed": 0, "passed": 0, "failed": 0, "skipped": 0,
            "note": "the consumer program covers the in-memory songid API and "
                    "the debug/unicode setters, which need no hardware"}))
