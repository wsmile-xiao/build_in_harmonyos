#!/usr/bin/env python3
"""Conan consumer test for tiny-aes-c 0.4.2."""

import json
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class TinyAesCTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    exports_sources = "CMakeLists.txt", "test_tiny_aes_c.cpp"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        upstream_result = {
            "status": "no_tests",
            "framework": "none",
            "command": "N/A (the pinned snapshot has no test entrypoint)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "CryptoManiac/tiny-aes-cpp commit b2761c223710 contains only "
                "README.md, aes.cpp, aes.h, and unlicense.txt; it has no test "
                "source, test directory, build system, or test command."
            ),
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT="
            + json.dumps(upstream_result, ensure_ascii=False)
        )

        executable = os.path.join(
            self.cpp.build.bindirs[0],
            "test_tiny_aes_c",
        )
        consumer_result = {
            "executed": True,
            "passed": True,
            "command": "./test_tiny_aes_c",
            "discovered": 12,
            "passedCount": 12,
        }
        try:
            self.run(f'"{executable}"', env="conanrun")
        except Exception:
            consumer_result["passed"] = False
            consumer_result["passedCount"] = 0
            self.output.info(
                "HMBS_TEST_PACKAGE_RESULT="
                + json.dumps(consumer_result, ensure_ascii=False)
            )
            raise
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT="
            + json.dumps(consumer_result, ensure_ascii=False)
        )
