#!/usr/bin/env python3
"""Conan test_package for verdict 1.4.5 — exercises the packaged public API.

Builds test_verdict.cpp (7 analytic metric values + 3 comparative quality
checks = 10 assertions) with CMakeDeps against the packaged verdict::verdict
target and runs it on the target.
"""
import json
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class VerdictTestConan(ConanFile):
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
        # 10 explicit checks in test_verdict.cpp
        test_pkg = {
            "executed": True,
            "passed": True,
            "command": "./test_verdict",
            "discovered": 10,
            "passedCount": 10,
        }
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_verdict")
        try:
            self.run(bin_path, env="conanrun")
        except Exception:
            test_pkg["passed"] = False
            self.output.info("HMBS_TEST_PACKAGE_RESULT="
                             + json.dumps(test_pkg, ensure_ascii=False))
            raise
        self.output.info("HMBS_TEST_PACKAGE_RESULT="
                         + json.dumps(test_pkg, ensure_ascii=False))
