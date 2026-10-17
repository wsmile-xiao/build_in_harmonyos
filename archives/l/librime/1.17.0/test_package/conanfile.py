#!/usr/bin/env python3
"""Conan test_package — librime 1.17.0 (CMake, consumer L1 test).

L1 test: builds a small C++ program that calls librime's public C API
(rime_get_api / get_version / get_shared_data_dir_s) and validates the
returned values, proving the installed library links and runs on OHOS.

Emits HMBS machine-evidence markers:
  - HMBS_TEST_PACKAGE_RESULT   (consumer checks above)
  - HMBS_UPSTREAM_TEST_RESULT  (re-emitted from the package's res/ file,
                               written by the main recipe after ctest ran)
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout

# Consumer smoke checks exercised by test.cpp:
#   1. rime_get_api() returns a valid RimeApi*
#   2. api->get_version() returns a non-empty version string
#   3. api->get_shared_data_dir_s() returns a non-empty data dir string
TEST_PACKAGE_CHECKS = 3


class LibrimeTestConan(ConanFile):
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
        test_binary = os.path.join(self.cpp.build.bindir, "test_librime")
        self.run(test_binary, env="conanrun")

        # HMBS machine-evidence marker for the consumer (L1) test.
        tp_marker = {
            "executed": True,
            "passed": True,
            "command": "test_librime (consumer smoke: api/version/shared-data-dir)",
            "discovered": TEST_PACKAGE_CHECKS,
            "passedCount": TEST_PACKAGE_CHECKS,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(tp_marker, ensure_ascii=False))
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(tp_marker, ensure_ascii=False), flush=True)

        # Re-emit the upstream test result persisted by the main recipe
        # (res/upstream_test_result.json — written by build() after the
        # upstream ctest suite ran).
        upstream_json = os.path.join(
            self.dependencies["librime"].package_folder,
            "res", "upstream_test_result.json")
        if not os.path.isfile(upstream_json):
            raise ConanException(
                f"upstream_test_result.json missing from package res/: {upstream_json}")
        with open(upstream_json, "r", encoding="utf-8") as fh:
            ut_marker = json.load(fh)
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(ut_marker, ensure_ascii=False))
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(ut_marker, ensure_ascii=False), flush=True)
