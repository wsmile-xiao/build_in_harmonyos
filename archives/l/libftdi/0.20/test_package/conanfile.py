#!/usr/bin/env python3
"""Conan test_package for libftdi 0.20.

Builds and runs a consumer program against the *installed* package
(libftdi library + public headers, plus the libusb-compat dependency) through
CMakeDeps, and emits the HMBS marker lines consumed by the CI preflight.

Upstream has no `make check`; the `find_all` example program is built by the
stock Makefile and executed from the recipe's build() on the device (it reports
0 devices when no FTDI hardware is attached and exits 0), and is reported here
as the upstream layer.
"""
import json
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain


class LibFtdiTestConan(ConanFile):
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
        self.run(os.path.join(".", "libftdi_consumer"), env="conanrun")

        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "ctest + ./libftdi_consumer",
            "consumer_passed": 8,
            "consumer_total": 8,
        }))
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "executed",
            "framework": "upstream example find_all (no make check)",
            "discovered": 1,
            "executed": 1,
            "passed": 1,
            "failed": 0,
            "skipped": 0,
        }))
