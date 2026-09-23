#!/usr/bin/env python3
"""Conan test_package — nbytes 0.1.4 consumer test.

Builds test.cpp against the packaged libnbytes (CMakeDeps + CMakeToolchain),
runs it on the native OHOS target and counts the per-check "CHECK-OK:" lines
for the HMBS_TEST_PACKAGE_RESULT machine-evidence marker (exit-0-alone is
not proof: all 18 CHECK-OK lines are required for a pass).

Upstream evidence: the recipe's build() already ran the upstream ctest suite
and persisted build_folder/hmbs_upstream.json into package/res/; this
test_package re-emits that marker every round (cache-hit rounds skip the main
build, the gate still needs the marker).
"""

import json
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout

# test.cpp performs exactly 18 CHECK() assertions, each printing one
# "CHECK-OK: <name>" line on success.
CONSUMER_CHECK_COUNT = 18


class NbytesTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _ensure_writable_tmp(self):
        # HMBS injects a task-private writable TMPDIR on the real
        # machine; prefer it, fall back to a dir under build_folder.
        for key in ("TMPDIR", "TMP", "TEMP"):
            candidate = os.environ.get(key)
            if candidate and os.path.isdir(candidate):
                tmp = candidate
                break
        else:
            tmp = None
        if not tmp:
            tmp = os.path.join(self.build_folder, "hmbs-tmp")
            os.makedirs(tmp, exist_ok=True)
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmp
        return tmp

    def build(self):
        self._ensure_writable_tmp()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _emit_upstream_marker(self):
        marker = None
        try:
            pkg = self.dependencies[self.tested_reference_str].package_folder
            evidence = os.path.join(str(pkg), "res", "hmbs_upstream.json")
            if os.path.isfile(evidence):
                with open(evidence, "r", encoding="utf-8") as handle:
                    marker = json.load(handle)
        except Exception:
            marker = None
        if not isinstance(marker, dict) or "status" not in marker:
            # Fallback: audit fact — upstream tests/basic.cpp declares 3
            # gtest TESTs; the recipe's build() runs them via ctest.
            # test_package re-emits a passed marker only from real package
            # evidence above; without it, report honestly as unknown.
            marker = {
                "status": "unknown",
                "framework": "ctest",
                "command": "ctest --output-on-failure",
                "discovered": 3,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "package res/hmbs_upstream.json not found; "
                "see build-phase HMBS_UPSTREAM_TEST_RESULT for evidence",
            }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False)
        )

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile/link test completed")
            return
        self._ensure_writable_tmp()
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_nbytes")
        if not os.path.isfile(bin_path):
            raise ConanException("test binary missing: %s" % bin_path)
        proc = subprocess.run(
            [bin_path],
            env=dict(os.environ),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=300,
        )
        output = proc.stdout or ""
        self.output.info(output[-2000:])
        ok_count = output.count("CHECK-OK:")
        marker = {
            "executed": True,
            "passed": proc.returncode == 0 and ok_count == CONSUMER_CHECK_COUNT,
            "command": bin_path,
            "discovered": CONSUMER_CHECK_COUNT,
            "passedCount": ok_count,
        }
        msg = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
        print(msg, flush=True)
        self.output.info(msg)
        # L0d quality gate: prove the binary also executes under the
        # conanrun environment.
        self.run(bin_path, env="conanrun")
        self._emit_upstream_marker()
        if not marker["passed"]:
            raise ConanException(
                "consumer test failed: rc=%s ok=%s/%s"
                % (proc.returncode, ok_count, CONSUMER_CHECK_COUNT)
            )
        self.output.info("nbytes consumer test_package passed")
