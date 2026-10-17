#!/usr/bin/env python3
"""Conan test_package — cpp-jwt 1.5.1 consumer verification."""
import json
import os
import re
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class CppJwtTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            cmake = CMake(self)
            cmake.test()
            # Also run the test binaries directly (L0d requires an actual self.run call)
            self.run(os.path.join(self.cpp.build.bindirs[0], "test_cpp-jwt"), env="conanrun")
            self.run(os.path.join(self.cpp.build.bindirs[0], "ohos_adapt_test"), env="conanrun")
            self._emit_test_package_marker()
            self._reemit_upstream_marker()

    def _emit_test_package_marker(self):
        # HMBS hard gate: HMBS_TEST_PACKAGE_RESULT with real consumer counts.
        # test_package/CMakeLists.txt registers 2 ctest cases
        # (test_cpp-jwt + ohos_adapt_test); numbers below are parsed from a
        # real ctest run, never assumed.
        raw = ""
        try:
            proc = subprocess.run(
                ["ctest", "--output-on-failure"],
                cwd=self.build_folder, capture_output=True,
                text=True, timeout=600)
            raw = (proc.stdout or "") + (proc.stderr or "")
        except Exception as exc:
            self.output.warning("cpp-jwt test_package: ctest parse run failed: %s" % exc)
        total = failed = 0
        m = re.search(
            r"(\d+)% tests? passed, (\d+) tests? failed out of (\d+)", raw)
        if m:
            failed = int(m.group(2))
            total = int(m.group(3))
        else:
            m2 = re.search(r"tests passed out of (\d+)", raw)
            if m2:
                total = int(m2.group(1))
        passed_count = total - failed if total else 0
        ok = total > 0 and failed == 0
        marker = {
            "executed": True,
            "passed": ok,
            "command": "ctest --output-on-failure",
            "discovered": total,
            "passedCount": passed_count,
        }
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))
        if not ok:
            raise ConanException(
                "cpp-jwt test_package ctest did not fully pass: %s" % raw[-2000:])

    def _reemit_upstream_marker(self):
        # Re-emit upstream evidence from the packaged res/ JSON so the marker
        # is present even when conan skips a cached build() ("Already
        # installed"). Missing JSON is an explicit failure, never a silent pass.
        dep = self.dependencies[self.tested_reference_str.split("/")[0]]
        result_path = os.path.join(
            dep.package_folder, "res", "hmbs_upstream_result.json")
        if not os.path.isfile(result_path):
            raise ConanException(
                "res/hmbs_upstream_result.json not found in package — "
                "upstream tests did not run during build(); refusing to pass silently")
        with open(result_path, "r", encoding="utf-8") as fh:
            upstream = json.load(fh)
        self.output.info("HMBS_UPSTREAM_TEST_RESULT="
                         + json.dumps(upstream, ensure_ascii=False))
