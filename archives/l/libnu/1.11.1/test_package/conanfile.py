#!/usr/bin/env python3
"""Conan test_package for libnu 1.11.1.

Builds test_libnu against the packaged nunicode::nu target and runs 5 real
consumer assertions (UTF-8 round-trip, UTF-16/32, validation, version).
Parses CASE PASS lines for HMBS_TEST_PACKAGE_RESULT, then re-emits the
upstream evidence persisted by the recipe build (no hardcoded copies).
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LibnuTestConan(ConanFile):
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
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: skip runtime test")
            return
        binary = os.path.join(self.cpp.build.bindirs[0], "test_libnu")
        log_path = os.path.join(self.build_folder, "test_libnu.log")
        try:
            self.run('"{}" > "{}" 2>&1'.format(binary, log_path), env="conanrun")
        except ConanException:
            pass
        out = ""
        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                out = f.read()
        except OSError:
            out = ""
        self.output.info("test output:\n" + out)
        discovered = 5
        passed_count = out.count("CASE PASS")
        marker = {
            "executed": True,
            "passed": discovered > 0 and passed_count == discovered,
            "command": "./test_libnu (libnu consumer checks)",
            "discovered": discovered,
            "passedCount": passed_count,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
        self._emit_upstream_result()
        if not marker["passed"]:
            raise ConanException(
                "test_package failed: {}/{} cases passed".format(passed_count, discovered))

    def _emit_upstream_result(self):
        dep = self.dependencies["libnu"]
        path = os.path.join(dep.package_folder, "res", "upstream_test_result.json")
        if not os.path.isfile(path):
            raise ConanException("upstream_test_result.json not found in package")
        with open(path, "r", encoding="utf-8") as f:
            result = json.load(f)
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result))
        ok_shape = (
            isinstance(result, dict)
            and result.get("status") == "passed"
            and int(result.get("discovered", 0)) > 0
            and int(result.get("executed", 0)) == int(result.get("discovered", 0))
            and int(result.get("passed", 0)) == int(result.get("discovered", 0))
            and int(result.get("failed", 0)) == 0
            and int(result.get("skipped", 0)) == 0
        )
        if not ok_shape:
            raise ConanException("upstream test evidence invalid: {}".format(result))
