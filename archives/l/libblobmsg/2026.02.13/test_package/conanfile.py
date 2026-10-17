#!/usr/bin/env python3
"""Conan test_package — libblobmsg 2026.02.13 (Conan L1 official test).

Consumer test (test.c) exercises blobmsg + blobmsg_json APIs with 13
check() assertions (any failure flips the exit code to 1, so rc 0 proves
all 13 passed). Machine evidence (HMBS preflight hard gate):
- HMBS_TEST_PACKAGE_RESULT with the real consumer-test counters.
- HMBS_UPSTREAM_TEST_RESULT re-emitted from the verdict recorded by the
  main recipe build() (package file hmbs_upstream_result.json), so the
  evidence survives Conan cache hits where build() is skipped.
Both markers are emitted dual-channel (raw print + self.output.info):
HMBS preflight scrapes raw stdout, so info-only emits are missed.
Failure paths emit failed markers BEFORE raising, so a consumer failure
or missing verdict file never surfaces as "missing evidence".
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout


class LibblobmsgTestConan(ConanFile):
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

    def _emit(self, name, payload):
        marker = name + "=" + json.dumps(payload, ensure_ascii=False)
        # Dual-channel: raw stdout for the HMBS scraper + conan log.
        print(marker, flush=True)
        self.output.info(marker)

    def test(self):
        # 13 check() assertions in test.c; rc 0 <=> all passed (any failed
        # check sets failed=1 and main returns 1).
        consumer_ok = True
        try:
            self.run(os.path.join(self.cpp.build.bindir, "test_libblobmsg"), env="conanrun")
        except Exception:
            consumer_ok = False
        marker = {
            "executed": True,
            "passed": consumer_ok,
            "command": "./test_libblobmsg (13 blobmsg/blobmsg_json API assertions)",
            "discovered": 13,
            "passedCount": 13 if consumer_ok else 0,
        }
        self._emit("HMBS_TEST_PACKAGE_RESULT", marker)

        # Re-emit the upstream suite verdict captured during build(); the
        # JSON is produced from real on-device execution, never guessed.
        # Always emit an UPSTREAM marker even when the consumer failed or
        # the verdict file is missing, so HMBS sees failed (diagnosable)
        # instead of incomplete (missing evidence).
        dep = self.dependencies["libblobmsg"]
        marker_file = os.path.join(str(dep.package_folder), "hmbs_upstream_result.json")
        upstream_marker = None
        upstream_ok = False
        if os.path.isfile(marker_file):
            try:
                with open(marker_file, encoding="utf-8") as f:
                    data = json.load(f)
                upstream_marker = {k: data.get(k) for k in
                                   ("status", "framework", "command", "discovered",
                                    "executed", "passed", "failed", "skipped")}
                if data.get("reason"):
                    upstream_marker["reason"] = data.get("reason")
                upstream_ok = (data.get("status") == "passed" and bool(data.get("executed")))
            except (OSError, ValueError) as exc:
                upstream_marker = {
                    "status": "failed",
                    "framework": "custom-c-unit",
                    "command": "read hmbs_upstream_result.json",
                    "discovered": 15,
                    "executed": 0,
                    "passed": 0,
                    "failed": 0,
                    "skipped": 0,
                    "reason": f"verdict file unreadable: {marker_file}: {exc}",
                }
        else:
            upstream_marker = {
                "status": "failed",
                "framework": "custom-c-unit",
                "command": "read hmbs_upstream_result.json",
                "discovered": 15,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": f"upstream test verdict missing: {marker_file} (recipe build() must run the suite)",
            }
        self._emit("HMBS_UPSTREAM_TEST_RESULT", upstream_marker)
        if not consumer_ok:
            raise ConanException("consumer test test_libblobmsg failed (see HMBS_TEST_PACKAGE_RESULT)")
        if not upstream_ok:
            raise ConanException(f"upstream suite did not pass: {upstream_marker}")
        self.output.info("test libblobmsg consumer + upstream evidence OK")
