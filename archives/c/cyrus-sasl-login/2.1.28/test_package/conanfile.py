#!/usr/bin/env python3
"""Conan test_package — cyrus-sasl-login 2.1.28 consumer test.

Builds test_login.c against the packaged static libsasl2 (CMakeDeps +
CMakeToolchain), runs it on the native OHOS target and counts the
per-check "CHECK-OK:" lines for the HMBS_TEST_PACKAGE_RESULT
machine-evidence marker (exit-0-alone is not proof: 6 CHECK-OK lines
are required for a pass).

Upstream evidence: cyrus-sasl 2.1.28 ships no automated test harness
(BLFS: "This package does not come with a test suite"; audit in
MANIFEST.yml), so this re-emits HMBS_UPSTREAM_TEST_RESULT with
status=no_tests on every run (cache-hit rounds skip the main build,
the gate still needs the marker).
"""

import json
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.cmake import CMake
from conan.tools.cmake import cmake_layout

# test_login.c performs exactly 6 checks, each printing one
# "CHECK-OK: <name>" line on success.
CONSUMER_CHECK_COUNT = 6


class CyrussaslloginTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _ensure_writable_tmp(self):
        # HMBS injects a task-private writable TMPDIR on the real
        # machine (/tmp is read-only: [readonly_tmp]). Prefer it in
        # every phase; fall back to a dir under build_folder so neither
        # CMake/ctest nor the test binary ever touches /tmp.
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
        # Keep CMake temp files off a possibly read-only /tmp.
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
                "cyrus-sasl 2.1.28 ships no automated test harness: "
                "no TEST/TEST_F, no ctest/meson/pytest wiring, no automake "
                "TESTS/check_PROGRAMS and no make check target "
                "(utils/testsuite and sample/ are manual interactive "
                "programs, BLFS confirms no test suite); "
                "see test_package/MANIFEST.yml upstream_test_audit"
            ),
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT="
            + json.dumps(upstream_marker, ensure_ascii=False)
        )

    def _dump_last_test_log(self):
        # ctest writes per-test output to Testing/Temporary/LastTest.log
        # under the build dir; surface it so the next preflight round can
        # see the real test_login failure without guessing.
        try:
            candidates = []
            build_folder = getattr(self, "build_folder", "") or ""
            if build_folder and os.path.isdir(build_folder):
                for root, dirs, files in os.walk(build_folder):
                    if "LastTest.log" in files:
                        candidates.append(os.path.join(root, "LastTest.log"))
                    # Keep the walk shallow: build trees are deep.
                    if root.count(os.sep) - build_folder.count(os.sep) > 6:
                        dirs[:] = []
            for log_path in sorted(candidates)[:2]:
                try:
                    with open(log_path, "r", encoding="utf-8",
                              errors="replace") as handle:
                        content = handle.read()
                except OSError:
                    continue
                self.output.info("LastTest.log (%s) tail:" % log_path)
                self.output.info(content[-4000:])
        except Exception:
            pass

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile/link test completed")
            return
        tmp = self._ensure_writable_tmp()
        self._log_package_libs_for_ohos()
        cmake = CMake(self)
        try:
            cmake.test()
        except Exception as exc:
            # Do not lose the evidence: dump the real ctest output and
            # still emit both machine markers (passed:false) so HMBS can
            # judge instead of marking the round incomplete.
            self.output.warning("ctest failed: %s" % exc)
            self._dump_last_test_log()
            self._run_consumer_binary(raise_on_failure=False)
            self._emit_upstream_marker()
            raise
        self._run_consumer_binary(raise_on_failure=True)
        # L0d quality gate: prove the binary also executes under the
        # conanrun environment (uses the same writable TMPDIR).
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_login")
        self.run(bin_path, env="conanrun")
        self._emit_upstream_marker()
        self.output.info("cyrus-sasl-login consumer test_package passed")

    def _log_package_libs_for_ohos(self):
        # Diagnose static-vs-shared mixups: the package must ship only
        # libsasl2.a (shared=False). Log it so the next preflight shows
        # whether a stale .so caused a DT_NEEDED libsasl2.so.3.
        try:
            pkg = self.dependencies[self.tested_reference_str].package_folder
        except Exception:
            try:
                pkg = self.dependencies["cyrus-sasl-login"].package_folder
            except Exception:
                return
        libdir = os.path.join(str(pkg), "lib")
        try:
            names = sorted(os.listdir(libdir))
        except OSError as exc:
            self.output.info("package libdir missing %s: %s" % (libdir, exc))
            return
        self.output.info("package libdir %s: %s" % (libdir, ", ".join(names)))

    def _run_consumer_binary(self, raise_on_failure):
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_login")
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
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
        )
        if not marker["passed"] and raise_on_failure:
            raise ConanException(
                "consumer test failed: rc=%s ok=%s/%s"
                % (proc.returncode, ok_count, CONSUMER_CHECK_COUNT)
            )
