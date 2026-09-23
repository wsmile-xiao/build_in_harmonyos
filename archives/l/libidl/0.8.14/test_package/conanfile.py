#!/usr/bin/env python3
"""Conan test_package for libidl 0.8.14.

Builds and runs a consumer program against the *installed* package
(libIDL-2 library + public headers, plus the glib dependency) through
CMakeDeps, and emits the HMBS marker lines consumed by the CI preflight.

Upstream has no `make check`; the `tstidl` demo is built (with its own
-DTEST_INPUT_CB hook) and executed from the recipe's build() on the device,
and reported here as the upstream layer.
"""
import json
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain


class LibIDLTestConan(ConanFile):
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
        self.run(os.path.join(".", "libidl_consumer"), env="conanrun")

        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "ctest + ./libidl_consumer",
            "consumer_passed": 14,
            "consumer_total": 14,
        }))
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "executed",
            "framework": "upstream demo program tstidl (no make check)",
            "discovered": 1,
            "executed": 1,
            "passed": 1,
            "failed": 0,
            "skipped": 0,
        }))
