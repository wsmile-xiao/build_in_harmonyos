#!/usr/bin/env python3
"""Conan test_package — librb 2.0.0 consumer verification.

Drives the installed librb through test_librb (6 real-API checks: heap
round-trip, count/space, stack init, growable, peek/discard, dynamic frame).
The binary's per-check "PASS:" lines are counted for the
HMBS_TEST_PACKAGE_RESULT machine-evidence marker (exit-0 alone is not proof).
Also re-emits the upstream suite result persisted by the main recipe in
res/upstream_test_result.json so evidence survives Conan cache hits.
"""
import json
import os
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout

CONSUMER_CHECK_COUNT = 6


class LibrbTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
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
        # Re-emit the upstream result persisted by the main recipe: on cache
        # hits build() is skipped and its marker never prints, but this
        # test() runs every round.
        dep = self.dependencies["librb"]
        res_json = os.path.join(dep.package_folder, "res", "upstream_test_result.json")
        if not os.path.isfile(res_json):
            raise RuntimeError("upstream_test_result.json missing from package res/")
        with open(res_json, "r", encoding="utf-8") as fh:
            upstream = json.load(fh)
        upstream_msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream)
        self.output.info(upstream_msg)
        print(upstream_msg, flush=True)
        if (upstream.get("status") != "passed"
                or int(upstream.get("discovered", 0)) <= 0
                or int(upstream.get("executed", 0)) != int(upstream.get("discovered", 0))
                or int(upstream.get("passed", 0)) != int(upstream.get("discovered", 0))):
            raise RuntimeError("upstream result invalid: %s" % upstream)

        test_bin = os.path.join(self.build_folder, "test_librb")
        if not os.path.isfile(test_bin):
            raise RuntimeError("test binary missing: %s" % test_bin)
        # L0d gate: real execution under the conanrun environment.
        self.run('"%s"' % test_bin, env="conanrun")
        # Count real per-check evidence (shared-lib runtime needs the
        # dependency libdir on the loader path for the capture run).
        libdirs = [os.path.join(dep.package_folder, "lib")]
        env = dict(os.environ)
        existing = env.get("LD_LIBRARY_PATH", "")
        env["LD_LIBRARY_PATH"] = ":".join(libdirs + ([existing] if existing else []))
        run = subprocess.run([test_bin], env=env, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True, timeout=300)
        output = run.stdout or ""
        self.output.info(output[-2000:])
        ok_count = output.count("PASS:")
        marker = {
            "executed": True,
            "passed": run.returncode == 0 and ok_count == CONSUMER_CHECK_COUNT,
            "command": test_bin,
            "discovered": CONSUMER_CHECK_COUNT,
            "passedCount": ok_count,
        }
        marker_msg = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker)
        self.output.info(marker_msg)
        print(marker_msg, flush=True)
        if not marker["passed"]:
            raise RuntimeError("consumer test failed: rc=%s ok=%s/%s"
                               % (run.returncode, ok_count, CONSUMER_CHECK_COUNT))
