#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Conan test_package — vineyard (v6d) 0.24.4 (CMake).

L1 test: verifies libvineyard_client loads and its public C++ API can be used
without a running vineyardd server. Emits the HMBS machine-evidence markers
(HMBS_TEST_PACKAGE_RESULT / HMBS_UPSTREAM_TEST_RESULT) for the CI PR reporter.
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout

# Consumer smoke checks executed by test_package.cpp:
#   1. vineyard_version() returns a non-empty version string
#   2. vineyard::Client default-construction (links libvineyard_client) and is
#      not Connected() without an explicit Connect()
#   3. InvalidObjectID() == numeric_limits<ObjectID>::max()
TEST_PACKAGE_CHECKS = 3


class VineyardTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        test_binary = os.path.join(self.cpp.build.bindirs[0], "test_vineyard")
        self.run(test_binary, env="conanrun")

        # HMBS machine-evidence markers for the CI PR reporter
        tp_marker = {
            "executed": True,
            "passed": True,
            "command": "test_vineyard (consumer smoke: version/Client-link/InvalidObjectID)",
            "discovered": TEST_PACKAGE_CHECKS,
            "passedCount": TEST_PACKAGE_CHECKS,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(tp_marker, ensure_ascii=False))
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(tp_marker, ensure_ascii=False), flush=True)

        # Re-emit the upstream test result persisted by the main recipe
        # (res/upstream_test_result.json — written by build() after the
        # upstream ctest suite passed).
        upstream_json = os.path.join(
            self.dependencies["vineyard"].package_folder,
            "res", "upstream_test_result.json")
        if not os.path.isfile(upstream_json):
            raise ConanException(
                f"upstream_test_result.json missing from package res/: {upstream_json}")
        with open(upstream_json, "r", encoding="utf-8") as fh:
            ut_marker = json.load(fh)
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(ut_marker, ensure_ascii=False))
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(ut_marker, ensure_ascii=False), flush=True)
