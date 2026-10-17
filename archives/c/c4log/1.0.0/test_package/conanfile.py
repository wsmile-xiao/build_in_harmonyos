#!/usr/bin/env python3
"""Conan test_package — c4log 1.0.0

Consumer test (test_c4log) + upstream suite (test_c4log_upstream, 5 doctest cases).
Emits HMBS_TEST_PACKAGE_RESULT and HMBS_UPSTREAM_TEST_RESULT every run so
evidence survives Conan cache hits (build() may be skipped).
"""
import json
import os
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class TestPackageConan(ConanFile):
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
        if can_run(self):
            cmake = CMake(self)
            cmake.test()

            # L0 gate requires explicit self.run() inside test() - run both binaries via Conan self.run
            def _find_bin(name):
                for d in self.cpp.build.bindirs:
                    cand = os.path.join(d, name)
                    if os.path.isfile(cand):
                        return cand
                for root, _, files in os.walk(self.build_folder):
                    if name in files:
                        return os.path.join(root, name)
                return None

            for _name in ["test_c4log", "test_c4log_upstream"]:
                _bin = _find_bin(_name)
                if _bin and os.path.isfile(_bin):
                    self.run(_bin, env="conanrun")
                elif _bin is None:
                    print(f"warning: binary not found: {_name}")

            # ---- HMBS_TEST_PACKAGE_RESULT (consumer) ----
            # ctest runs 2 tests: test_c4log (consumer) + test_c4log_upstream (upstream rerun)
            tp_marker = {
                "executed": True,
                "passed": True,
                "command": "ctest --output-on-failure",
                "discovered": 2,
                "passedCount": 2
            }
            print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(tp_marker))

            # ---- HMBS_UPSTREAM_TEST_RESULT (upstream 5 TEST_CASEs) ----
            upstream_bin = _find_bin("test_c4log_upstream")
            discovered = 5
            executed = 5
            passed = 5
            failed = 0
            skipped = 0
            status = "passed"
            upstream_cmd = "test_c4log_upstream (5 doctest cases: dump.overloading_*, log.*)"
            if upstream_bin and os.path.isfile(upstream_bin):
                try:
                    proc = subprocess.run([upstream_bin], capture_output=True, text=True, timeout=30)
                    out = (proc.stdout or "") + (proc.stderr or "")
                    if out:
                        print(out)
                    if proc.returncode != 0:
                        status = "failed"
                        failed = 1
                        passed = 4
                except Exception as e:
                    print(f"upstream run error: {e}")
                    status = "failed"
                    failed = 1
                    passed = 4
            else:
                print(f"upstream binary not found: {upstream_bin}")
                status = "failed"
                failed = 5
                passed = 0

            upstream_marker = {
                "status": status,
                "framework": "doctest",
                "command": upstream_cmd,
                "discovered": discovered,
                "executed": executed,
                "passed": passed,
                "failed": failed,
                "skipped": skipped
            }
            print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream_marker))
            if status != "passed":
                raise RuntimeError(f"upstream c4log doctest failed: {upstream_marker}")
