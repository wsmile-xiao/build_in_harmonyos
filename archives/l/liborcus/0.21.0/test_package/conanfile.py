#!/usr/bin/env python3
"""Conan test_package for liborcus 0.21.0 — consumer verification (R34).

Builds test_orcus.cpp against the packaged libraries via CMake and runs
it on the real OHOS aarch64 target. The binary performs 15 real API
assertions (CSV/JSON/SAX parsing, string interning, base64 codec), each
emitting an "ORCUS-CHECK <name> ok" line; this test() counts those lines
for the HMBS_TEST_PACKAGE_RESULT marker and re-emits the persisted
HMBS_UPSTREAM_TEST_RESULT marker from the package res/ directory, so
both evidences are present on every run even when conan skips a cached
build() ("Already installed!").
"""

import json
import os
import re
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout

EXPECTED_CHECKS = 15


class LiborcusTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        # Resolve the real OHOS aarch64 clang dynamically — same principle
        # as the mdds recipe. The profile may pin a device path that does
        # not exist in this build sandbox; fall back to PATH lookup of the
        # same compiler name. Never hardcode user/storage paths.
        raw = self.conf.get("tools.build:compiler_executables",
                            check_type=dict)

        def resolve_compiler(lang):
            cand = None
            if raw:
                cand = raw.get(lang) or raw.get(lang.upper())
            if cand and os.path.isfile(cand):
                return cand
            base = (os.path.basename(cand) if cand
                    else ("clang" if lang == "c" else "clang++"))
            return shutil.which(base)

        cc = resolve_compiler("c")
        cxx = resolve_compiler("cpp")
        if str(self.settings.os) == "OHOS":
            for label, path in (("CC", cc), ("CXX", cxx)):
                if not (path and os.path.isfile(path)):
                    raise ConanException(
                        "%s not found: %r" % (label, path))
                proc = subprocess.run(
                    [path, "-print-target-triple"],
                    capture_output=True, text=True)
                triple = (proc.stdout or "").strip()
                if proc.returncode != 0 or triple != "aarch64-unknown-linux-ohos":
                    raise ConanException(
                        "%s is not an OHOS aarch64 compiler "
                        "(triple=%r, path=%r)" % (label, triple, path))
        if cc:
            tc.variables["CMAKE_C_COMPILER"] = cc
        if cxx:
            tc.variables["CMAKE_CXX_COMPILER"] = cxx
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("Cross-building: skip runtime execution")
            return
        # Consumer binary built by CMake (same idiom as libwpd 0.10.3).
        binary = os.path.join(self.cpp.build.bindirs[0], "test_orcus")
        # Capture the output to count the per-check evidence lines; the
        # exit code alone is not evidence (a silent exit 0 proves nothing).
        proc = subprocess.run([binary], capture_output=True, text=True)
        output = (proc.stdout or "") + (proc.stderr or "")
        self.output.info(output[-3000:] if output else "")
        if proc.returncode != 0:
            raise ConanException(
                "test_orcus exited with code %d" % proc.returncode)
        passed = len(re.findall(r"^ORCUS-CHECK \S+ ok$", output,
                                flags=re.M))
        if passed != EXPECTED_CHECKS:
            raise ConanException(
                "test_orcus printed %d/%d ORCUS-CHECK ok lines; "
                "refusing to pass silently" % (passed, EXPECTED_CHECKS))
        # CI L0d requires the test program to be executed via self.run as
        # well; the captured run above validates the output, this re-run
        # through Conan fails the package on a non-zero exit.
        self.run(binary, env="conanrun")
        tp_result = {
            "executed": True,
            "passed": passed == EXPECTED_CHECKS,
            "command": "./test_orcus",
            "discovered": EXPECTED_CHECKS,
            "passedCount": passed,
        }
        line = "HMBS_TEST_PACKAGE_RESULT=%s" % json.dumps(tp_result)
        print(line, flush=True)
        self.output.info(line)
        # Re-emit the upstream evidence persisted by build() into
        # <package>/res/upstream_test_result.json, validated before
        # re-emitting (hard-gate fields).
        dep = self.dependencies["liborcus"]
        result_path = os.path.join(dep.package_folder, "res",
                                   "upstream_test_result.json")
        if not os.path.isfile(result_path):
            raise ConanException(
                "upstream_test_result.json not found in package (%s) — "
                "upstream tests did not run during build(); refusing to "
                "pass silently" % result_path)
        with open(result_path, "r", encoding="utf-8") as handle:
            upstream = json.load(handle)
        for key in ("status", "framework", "command", "discovered",
                    "executed", "passed", "failed", "skipped"):
            if key not in upstream:
                raise ConanException(
                    "upstream_test_result.json missing key %r" % key)
        if (not isinstance(upstream["discovered"], int)
                or upstream["discovered"] <= 0):
            raise ConanException(
                "upstream_test_result.json has invalid discovered=%r"
                % (upstream.get("discovered"),))
        if upstream["executed"] < upstream["discovered"]:
            raise ConanException(
                "upstream_test_result.json executed < discovered (%r < %r)"
                % (upstream.get("executed"), upstream.get("discovered")))
        upstream_line = "HMBS_UPSTREAM_TEST_RESULT=%s" % json.dumps(
            upstream, ensure_ascii=False)
        print(upstream_line, flush=True)
        self.output.info(upstream_line)
