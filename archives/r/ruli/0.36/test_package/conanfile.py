#!/usr/bin/env python3
"""Conan test_package - ruli 0.36 consumer test.

Builds test_ruli.c against the *packaged* libruli (and, transitively, the
packaged liboop headers that <ruli.h> requires) with CMakeDeps +
CMakeToolchain, runs it on the native OHOS target, and counts the per-check
"CHECK-OK:" / "CHECK-SKIP:" / "CHECK-FAIL:" lines for the
HMBS_TEST_PACKAGE_RESULT machine-evidence marker.  Exit code 0 alone is not
proof: the run only passes when ok + skipped == 12, failed == 0 and ok > 0.

Upstream evidence: ruli 0.36 ships no automated test suite at all (no check /
test target in Makefile, src/Makefile, tools/Makefile or sample/Makefile; audit
in MANIFEST.yml), so HMBS_UPSTREAM_TEST_RESULT with status=no_tests is emitted
BEFORE the consumer binary runs, and it therefore survives a consumer crash.
"""

import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout

# test_ruli.c performs exactly 12 checks, each printing exactly one
# "CHECK-OK: <name>" / "CHECK-SKIP: <name>" line (never both).  Only check 11
# (the live ruli_sync_query() NXDOMAIN round trip) can be skipped; everything
# else is deterministic.
CONSUMER_CHECK_COUNT = 12
NETWORK_CHECKS = 1


class RuliTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # E092 family (liboop 1.0.1 / ayatana-ido proven): the CI profile bakes
        # CMAKE_C_COMPILER=/data/service/hnp/bin/clang, which does not exist
        # inside a sandboxed preflight run, so CMake declares the compiler
        # broken at project().  Keep the profile value when the file really is
        # there (CI behaviour unchanged), otherwise fall back to the
        # PATH-visible compiler.  Existence-only probe: HMDFS ignores chmod so
        # os.access(X_OK) is permanently False there (R49).
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        try:
            exes = self.conf.get("tools.build:compiler_executables",
                                 default=None)
        except Exception:
            exes = None
        conf_c = conf_cxx = None
        if isinstance(exes, dict):
            conf_c = exes.get("c")
            conf_cxx = exes.get("cpp") or exes.get("cxx") or exes.get("c")
        for key, conf_val, bare in (
                ("CMAKE_C_COMPILER", conf_c, "clang"),
                ("CMAKE_CXX_COMPILER", conf_cxx, "clang++")):
            usable = False
            if conf_val and ("/" in str(conf_val) or os.path.sep in str(conf_val)):
                try:
                    usable = os.path.isfile(str(conf_val))
                except Exception:
                    usable = False
            if not usable:
                which = shutil.which(bare)
                if which:
                    tc.variables[key] = which
                    self.output.info(
                        "test_package compiler fallback: %s -> %s"
                        % (key, which))
                elif conf_val:
                    self.output.warning(
                        "conf compiler '%s' unusable and no %s on PATH"
                        % (conf_val, bare))
        tc.generate()

    def _ensure_writable_tmp(self):
        for key in ("TMPDIR", "TMP", "TEMP"):
            candidate = os.environ.get(key)
            if candidate and os.path.isdir(candidate):
                tmp = candidate
                break
        else:
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
        marker = {
            "status": "no_tests",
            "framework": "none (bare recursive Makefiles, no configure)",
            "command": "none: `make check` / `make test` are undefined targets",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "ruli 0.36 ships no automated test harness: the release "
                "tarball has no tests/ or test/ directory, no TESTS / "
                "check_PROGRAMS / check-local target and no DejaGnu or "
                "cUnit wiring; none of Makefile, src/Makefile, "
                "tools/Makefile or sample/Makefile defines a check or test "
                "rule (see test_package/MANIFEST.yml upstream_test_audit). "
                "build() therefore invokes no check target "
                "(upstream_test_in_build: false)."
            ),
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT="
            + json.dumps(marker, ensure_ascii=False)
        )

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile/link test completed")
            return
        self._ensure_writable_tmp()
        # Upstream evidence first: it stays in the log even if the consumer
        # binary below hangs and the harness kills the process group.
        self._emit_upstream_marker()

        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_ruli")
        if not os.path.isfile(bin_path):
            raise ConanException("consumer binary not found at %s" % bin_path)

        # L0d/PF3: prove the binary also executes under the conanrun env
        # (libruli.so, if built shared, must resolve through it).
        conanrun_ok = True
        conanrun_detail = "ok"
        try:
            self.run(bin_path, env="conanrun")
        except Exception as exc:
            conanrun_ok = False
            conanrun_detail = str(exc)[-500:]
            self.output.warning(
                "conanrun execution failed: %s" % conanrun_detail)

        proc = subprocess.run(
            [bin_path],
            env=dict(os.environ),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=600,
        )
        output = proc.stdout or ""
        self.output.info(output[-4000:])

        # Falsification guard: reference output must be non-empty.
        if not output.strip():
            raise ConanException("consumer test produced empty output")

        ok_count = output.count("CHECK-OK:")
        skip_count = output.count("CHECK-SKIP:")
        fail_count = output.count("CHECK-FAIL:")
        accounted = ok_count + skip_count + fail_count
        passed = (conanrun_ok and proc.returncode == 0 and fail_count == 0
                  and accounted == CONSUMER_CHECK_COUNT
                  and ok_count > 0)
        marker = {
            "executed": True,
            "passed": passed,
            "command": bin_path,
            "discovered": CONSUMER_CHECK_COUNT,
            "passedCount": ok_count,
            "skippedCount": skip_count,
            "failedCount": fail_count,
            "network_dependent_checks": NETWORK_CHECKS,
            "skip_reasons": [ln.split("|", 1)[1].strip()
                             for ln in output.splitlines()
                             if ln.startswith("CHECK-SKIP:")],
        }
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))
        if not passed:
            raise ConanException(
                "consumer test failed: conanrun_ok=%s rc=%s ok=%d skip=%d "
                "fail=%d accounted=%d/%d" % (
                    conanrun_ok, proc.returncode, ok_count, skip_count,
                    fail_count, accounted, CONSUMER_CHECK_COUNT))
        self.output.info("ruli consumer test_package passed (%d/%d checks)"
                         % (ok_count, CONSUMER_CHECK_COUNT))
