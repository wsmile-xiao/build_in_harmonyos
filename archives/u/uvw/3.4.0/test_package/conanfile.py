#!/usr/bin/env python3
"""Conan test_package for uvw 3.4.0 — consumer event-loop test.

Builds test_uvw.cpp against the packaged headers (uvw::uvw + libuv::libuv)
and runs four real event-loop assertions. Parses the CASE PASS lines from the
captured log for the HMBS_TEST_PACKAGE_RESULT marker, then re-emits the
upstream evidence persisted by the recipe build (no hardcoded copies of those
numbers).
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class UvwTestConan(ConanFile):
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
        CMakeDeps(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        # Same OOM guard as the main recipe: keep peak RSS minimal.
        cmake.build(cli_args=["--parallel", "1"], build_tool_args=["-j1"])

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: skip runtime test")
            return
        binary = os.path.join(self.cpp.build.bindirs[0], "test_uvw")
        log_path = os.path.join(self.build_folder, "test_uvw.log")
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
            "command": "./test_uvw (libuv link + loop/timer event-loop round-trip)",
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
        dep = self.dependencies["uvw"]
        path = os.path.join(dep.package_folder, "res", "upstream_test_result.json")
        if not os.path.isfile(path):
            raise ConanException("upstream_test_result.json not found in package")
        with open(path, "r", encoding="utf-8") as f:
            result = json.load(f)
        # Upstream caliber N=121 (gtest cases: 113 built + 8 dns unbuilt).
        # executed = passed + failed; skipped = gtest SKIPPED + 8 dns;
        # executed + skipped == discovered when the run is complete.
        # rule4: status must match the numbers — "passed" only at 100%
        # (skipped == 0); explained skips report "incomplete" with gaps[]
        # (environment / ohos_feature), which is accepted, not a failure.
        # Only "failed" (real failures or unaccounted remainder) rejects.
        try:
            discovered = int(result.get("discovered", -1))
            executed = int(result.get("executed", -1))
            passed = int(result.get("passed", -1))
            failed = int(result.get("failed", -1))
            skipped = int(result.get("skipped", -1))
        except (TypeError, ValueError):
            discovered = executed = passed = failed = skipped = -1
        gaps = result.get("gaps", [])
        gaps_sum = sum(int(g.get("count", 0)) for g in gaps) if isinstance(gaps, list) else -1
        status = result.get("status")
        # "passed" requires 100% (no skips, no gaps remainder);
        # "incomplete" requires full accounting via gaps (sum == unpassed).
        status_ok = (
            (status == "passed" and skipped == 0 and gaps_sum in (0, -1))
            or (status == "incomplete" and skipped > 0)
        )
        ok_shape = (
            isinstance(result, dict)
            and status_ok
            and result.get("framework") == "gtest"
            and discovered == 121
            and passed >= 0 and failed == 0 and executed >= 0 and skipped >= 0
            and passed + failed == executed
            and executed + skipped == discovered
            and isinstance(gaps, list) and gaps_sum == discovered - passed
            and all(g.get("category") in ("environment", "ohos_feature", "test_failure") for g in gaps)
        )
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result))
        if not ok_shape:
            raise ConanException(f"upstream test evidence invalid: {result}")
