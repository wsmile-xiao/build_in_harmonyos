#!/usr/bin/env python3
"""Conan test_package — libcerfcpp 3.3 consumer test.

Builds test_cerfcpp.cpp against the packaged libcerfcpp (CMakeDeps +
CMakeToolchain), runs it on the native OHOS target and counts the
per-check "CHECK-OK:" lines for the HMBS_TEST_PACKAGE_RESULT
machine-evidence marker (exit-0-alone is not proof: 6 CHECK-OK lines
are required for a pass).

Upstream evidence: the main recipe runs the upstream ctest suite in
build() and persists the real counts to res/hmbs_upstream.json; this
test() re-emits HMBS_UPSTREAM_TEST_RESULT from that file on every run
(cache-hit rounds skip the main build, the gate still needs the marker).
"""

import json
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout

# test_cerfcpp.cpp performs exactly 6 checks, each printing one
# "CHECK-OK: <name>" line on success.
CONSUMER_CHECK_COUNT = 6


class LibcerfcppTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _ensure_writable_tmp(self):
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
        dep = self.dependencies["libcerfcpp"]
        jf = os.path.join(dep.package_folder, "res", "hmbs_upstream.json")
        if not os.path.isfile(jf):
            raise ConanException(
                "[libcerfcpp] hmbs_upstream.json missing from package; "
                "upstream tests did not run in build()"
            )
        with open(jf, encoding="utf-8") as handle:
            up_result = json.load(handle)
        msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(up_result)
        print(msg, flush=True)
        self.output.info(msg)
        if up_result.get("status") != "passed":
            raise ConanException(
                "[libcerfcpp] upstream tests not passed: %s"
                % json.dumps(up_result)
            )

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile/link test completed")
            return
        self._ensure_writable_tmp()
        cmake = CMake(self)
        cmake.test()
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_cerfcpp")
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
        msg = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker)
        print(msg, flush=True)
        self.output.info(msg)
        # L0d gate requires a literal self.run() executing the real test
        # binary (subprocess above captures output for CHECK-OK counting;
        # this runs the same binary via Conan for L0d/L1b evidence).
        self.run(bin_path, env="conanrun")
        if not marker["passed"]:
            raise ConanException(
                "consumer test failed: rc=%s ok=%s/%s"
                % (proc.returncode, ok_count, CONSUMER_CHECK_COUNT)
            )
        self._emit_upstream_marker()
        self.output.info("libcerfcpp consumer test_package passed")
