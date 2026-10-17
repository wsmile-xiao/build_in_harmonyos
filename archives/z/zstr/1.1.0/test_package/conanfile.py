#!/usr/bin/env python3
"""Conan test_package for zstr 1.1.0 — consumer round-trip test.

Builds test_zstr.cpp against the packaged headers (zstr::zstr) and runs
four real compression round-trip assertions (file-based + in-memory).
Parses the CASE PASS lines from the captured log for the
HMBS_TEST_PACKAGE_RESULT marker, then re-emits the upstream evidence
persisted by the recipe build (no hardcoded copies of those numbers).
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class ZstrTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()
        deps = CMakeDeps(self)
        # The in-tree zlib recipe exposes the default `zlib::zlib` target;
        # remap to the canonical FindZLIB names used by zstr upstream
        # (same remap as quazip/1.4.1 test_package).
        deps.set_property("zlib", "cmake_file_name", "ZLIB")
        deps.set_property("zlib", "cmake_target_name", "ZLIB::ZLIB")
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: skip runtime test")
            return
        binary = os.path.join(self.cpp.build.bindirs[0], "test_zstr")
        log_path = os.path.join(self.build_folder, "test_zstr.log")
        try:
            self.run(f'"{binary}" > "{log_path}" 2>&1', env="conanrun")
        except ConanException:
            pass
        out = ""
        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                out = f.read()
        except OSError:
            out = ""
        self.output.info("test output:\n" + out)
        discovered = 4
        passed_count = out.count("CASE PASS")
        marker = {
            "executed": True,
            "passed": discovered > 0 and passed_count == discovered,
            "command": "./test_zstr (zstr file + memory round-trips)",
            "discovered": discovered,
            "passedCount": passed_count,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
        self._emit_upstream_result()
        if not marker["passed"]:
            raise ConanException(
                f"test_package failed: {passed_count}/{discovered} cases passed"
            )

    def _emit_upstream_result(self):
        dep = self.dependencies["zstr"]
        path = os.path.join(dep.package_folder, "res",
                            "upstream_test_result.json")
        if not os.path.isfile(path):
            raise ConanException(
                "upstream_test_result.json not found in package")
        with open(path, "r", encoding="utf-8") as f:
            result = json.load(f)
        ok_shape = (
            isinstance(result, dict)
            and result.get("status") == "passed"
            and int(result.get("discovered", 0)) == 29
            and int(result.get("executed", 0)) == 29
            and int(result.get("passed", 0)) == 29
            and int(result.get("failed", 0)) == 0
            and int(result.get("skipped", 0)) == 0
        )
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result))
        if not ok_shape:
            raise ConanException(f"upstream test evidence invalid: {result}")
