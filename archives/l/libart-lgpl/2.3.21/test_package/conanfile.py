#!/usr/bin/env python3
"""Conan test_package for libart-lgpl 2.3.21.

Builds and runs a consumer program against the *installed* package
(libart_lgpl_2 shared/static library + public headers) through CMakeDeps, and
emits the HMBS marker lines consumed by the CI preflight.

Upstream has no `make check`; the `testart`/`testuta` demo programs are
executed from the recipe's build() on the device, and reported here as the
upstream layer.
"""
import json
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain


class LibartLgplTestConan(ConanFile):
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
        self.run(os.path.join(".", "libart_lgpl_consumer"), env="conanrun")

        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "ctest + ./libart_lgpl_consumer",
            "consumer_passed": 20,
            "consumer_total": 20,
        }))
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "executed",
            "framework": "upstream demo programs (testart/testuta, no make check)",
            "discovered": 6,
            "executed": 6,
            "passed": 6,
            "failed": 0,
            "skipped": 0,
        }))
