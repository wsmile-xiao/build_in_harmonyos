#!/usr/bin/env python3
"""Conan test_package for librtpi 1.0.0 — Conan L1 official test.

Builds a consumer that links librtpi through the CMakeDeps/CMakeToolchain
integration and runs it.  The consumer exercises the full public C API
(mutex fast path, contended PI futex lock/unlock, condvar requeue wait and
signal, timed-wait timeout, teardown); see test_rtpi.c for the phase list.
CI runs this automatically via `conan create`.
"""
import json
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibrtpiTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        # -j1: shared CI workers are memory-constrained; see recipe notes.
        self.conf.define("tools.build:jobs", 1)
        cmake.build()

    def test(self):
        for binary, label in (("test_rtpi", "api_smoke"),
                              ("consumer_checks", "consumer_c"),
                              ("consumer_cpp", "consumer_cpp")):
            path = os.path.join(self.cpp.build.bindirs[0], binary)
            self.run(path, env="conanrun")
        marker = {
            "executed": True,
            "passed": True,
            "command": "test_rtpi && consumer_checks && consumer_cpp",
            "discovered": 3,
            "passedCount": 3,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
