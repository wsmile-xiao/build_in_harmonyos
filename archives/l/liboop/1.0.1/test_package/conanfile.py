#!/usr/bin/env python3
"""Conan test_package — liboop 1.0.1 consumer test.

Builds test_liboop.c against the packaged static liboop (CMakeDeps +
CMakeToolchain), runs it on the native OHOS target and counts the
per-check "CHECK-OK:" lines for the HMBS_TEST_PACKAGE_RESULT
machine-evidence marker (exit-0-alone is not proof: 6 CHECK-OK lines
are required for a pass).

Upstream evidence: liboop 1.0.1 ships no automated test harness
(no TESTS/check_PROGRAMS, no ctest/meson/pytest wiring; only the manual
interactive test-oop sample — audit in MANIFEST.yml), so this emits
HMBS_UPSTREAM_TEST_RESULT with status=no_tests BEFORE running the consumer
binary (audit-based: survives a consumer crash in the log) on every run.
The consumer binary runs twice (conanrun env proof + captured counting run);
a crash in either still emits HMBS_TEST_PACKAGE_RESULT with passed=false.
"""

import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout

# test_liboop.c performs exactly 6 checks, each printing one
# "CHECK-OK: <name>" line on success.
CONSUMER_CHECK_COUNT = 6


class LiboopTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # E092 family (ayatana-ido proven): the profile bakes
        # CMAKE_C_COMPILER=/data/service/hnp/bin/clang, which does not
        # exist inside the preflight sandbox (CMake "compiler is broken"
        # at project()). Keep the profile value when the file exists
        # (CI unchanged); otherwise fall back to the PATH-visible
        # compiler. Existence-only probe: no X_OK check (HMDFS ignores
        # chmod, R49). Also force CMAKE_SYSTEM_NAME=Linux: cmake 4.4.3
        # ships no Platform/HarmonyOS.cmake ("System is unknown to
        # cmake"); the consumer test is plain POSIX C, so the alias is
        # safe. Only build-tool selection is touched; no test skipped.
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
            conf_cxx = (exes.get("cpp") or exes.get("cxx")
                        or exes.get("c"))
        for key, conf_val, bare in (
                ("CMAKE_C_COMPILER", conf_c, "clang"),
                ("CMAKE_CXX_COMPILER", conf_cxx, "clang++")):
            usable = False
            if conf_val and (os.path.sep in str(conf_val)
                             or "/" in str(conf_val)):
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
        upstream_marker = {
            "status": "no_tests",
            "framework": "autotools-make-check",
            "command": "make check (upstream provides no automated suite)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "liboop 1.0.1 ships no automated test harness: "
                "no tests/ directory, no automake TESTS/check_PROGRAMS, "
                "no ctest/meson/pytest wiring; test-oop.c is a manual "
                "interactive sample requiring stdin/signals "
                "(see test_package/MANIFEST.yml upstream_test_audit)"
            ),
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT="
            + json.dumps(upstream_marker, ensure_ascii=False)
        )

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile/link test completed")
            return
        self._ensure_writable_tmp()
        # Audit-based upstream evidence first: it stays in the log even if the
        # consumer binary below hangs and the harness SIGKILLs the process
        # (previously the marker was emitted last, so any crash produced
        # "discovered 0" with no upstream evidence at all).
        self._emit_upstream_marker()
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_liboop")
        # L0d/PF3: prove the binary also executes under the conanrun env.
        # Wrapped so a crash here still flows into the counting run below,
        # which always emits HMBS_TEST_PACKAGE_RESULT before failing.
        conanrun_ok = True
        conanrun_detail = "ok"
        try:
            self.run(bin_path, env="conanrun")
        except Exception as exc:
            conanrun_ok = False
            conanrun_detail = str(exc)[-500:]
            self.output.warning("conanrun execution failed: %s" % conanrun_detail)
        proc = subprocess.run(
            [bin_path],
            env=dict(os.environ),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=120,
        )
        output = proc.stdout or ""
        self.output.info(output[-2000:])
        # Falsification guard: reference output must be non-empty.
        if not output.strip():
            raise ConanException("consumer test produced empty output")
        ok_count = output.count("CHECK-OK:")
        passed = (conanrun_ok and proc.returncode == 0
                  and ok_count == CONSUMER_CHECK_COUNT)
        marker = {
            "executed": True,
            "passed": passed,
            "command": bin_path,
            "discovered": CONSUMER_CHECK_COUNT,
            "passedCount": ok_count,
        }
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
        )
        if not passed:
            raise ConanException(
                "consumer test failed: conanrun_ok=%s rc=%s ok=%s/%s" %
                (conanrun_ok, proc.returncode, ok_count, CONSUMER_CHECK_COUNT)
            )
        self.output.info("liboop consumer test_package passed")
