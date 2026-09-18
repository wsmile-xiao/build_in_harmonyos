#!/usr/bin/env python3
"""Conan test_package — isocline 1.1.0 consumer test.

Builds test_isocline.c against the packaged library (CMakeDeps +
CMakeToolchain), runs it on the native OHOS target and counts the
per-check "CHECK-OK:" lines for the HMBS_TEST_PACKAGE_RESULT
machine-evidence marker (exit-0-alone is not proof: 13 CHECK-OK lines
are required for a pass — 12 default-mode API assertions plus the
piped-stdin ic_readline end-to-end check).

Upstream evidence: isocline 1.1.0 ships no automated test harness
(no TEST/TEST_F, no ctest wiring, no make check target; test/ holds
interactive TTY demos only, audit in MANIFEST.yml), so this re-emits
HMBS_UPSTREAM_TEST_RESULT with status=no_tests on every run
(cache-hit rounds skip the main build, the gate still needs the
marker).
"""

import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.cmake import cmake_layout

# test_isocline.c performs 12 checks in default mode plus 1 check in
# --stdin-line mode, each printing one "CHECK-OK: <name>" line.
EXPECTED_DEFAULT_CHECKS = 12
EXPECTED_STDIN_CHECKS = 1
CONSUMER_CHECK_COUNT = EXPECTED_DEFAULT_CHECKS + EXPECTED_STDIN_CHECKS


class IsoclineTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def _resolve_tool_compiler(self, kind):
        # Consumer-side mirror of the main recipe: profile pins absolute
        # paths; healthy runners use them as-is, runners where they are
        # absent fall back to PATH discovery.
        try:
            configured = self.conf.get(
                "tools.build:compiler_executables:%s" % kind, check_type=str)
        except Exception:
            configured = None
        if configured:
            if os.path.exists(configured):
                return configured
            base = os.path.basename(configured)
            for cand in ([base]
                         + (["clang", "cc"] if kind == "c"
                            else ["clang++", "c++"])):
                found = shutil.which(cand)
                if found:
                    self.output.warning(
                        "configured %s compiler missing: %s; "
                        "falling back to PATH: %s" % (kind, configured, found))
                    return found
            return base
        default = "clang" if kind == "c" else "clang++"
        return shutil.which(default) or default

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_C_COMPILER"] = self._resolve_tool_compiler("c")
        tc.variables["CMAKE_CXX_COMPILER"] = self._resolve_tool_compiler("cpp")
        tc.generate()

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
        os.environ["CC"] = self._resolve_tool_compiler("c")
        os.environ["CXX"] = self._resolve_tool_compiler("cpp")
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _emit_upstream_marker(self):
        upstream_marker = {
            "status": "no_tests",
            "framework": "none",
            "command": "no upstream test target (see test_package/MANIFEST.yml audit)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "isocline 1.1.0 ships no automated test suite: no "
                "enable_testing/include(CTest)/add_test wiring, no "
                "automake TESTS/check_PROGRAMS and no make check target "
                "(test/ holds only the interactive example.c TTY demo, "
                "the test_colors.c visual palette demo and the "
                "Example.hs Haskell binding sample); "
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
        # see the real test_isocline failure without guessing.
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
        self._ensure_writable_tmp()
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
            self._run_consumer_checks(raise_on_failure=False)
            self._emit_upstream_marker()
            raise
        self._run_consumer_checks(raise_on_failure=True)
        # L0d quality gate: prove the binary also executes under the
        # conanrun environment (uses the same writable TMPDIR).
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_isocline")
        self.run('"%s"' % bin_path, env="conanrun")
        self._emit_upstream_marker()
        self.output.info("isocline consumer test_package passed")

    def _log_package_libs_for_ohos(self):
        # Diagnose static-vs-shared mixups: the package must ship only
        # libisocline.a (shared=False) or libisocline.so (shared=True).
        try:
            pkg = self.dependencies[self.tested_reference_str].package_folder
        except Exception:
            try:
                pkg = self.dependencies["isocline"].package_folder
            except Exception:
                return
        libdir = os.path.join(str(pkg), "lib")
        try:
            names = sorted(os.listdir(libdir))
        except OSError as exc:
            self.output.info("package libdir missing %s: %s" % (libdir, exc))
            return
        self.output.info("package libdir %s: %s" % (libdir, ", ".join(names)))

    def _run_consumer_checks(self, raise_on_failure):
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_isocline")
        if not os.path.isfile(bin_path):
            raise ConanException("test binary missing: %s" % bin_path)
        ok_count = 0
        all_ok = True
        # Run 1: default mode (12 non-interactive API assertions).
        default_out, default_rc = self._run_capture([bin_path])
        default_ok = default_out.count("CHECK-OK:")
        self.output.info(default_out[-2000:])
        if default_rc != 0 or default_ok != EXPECTED_DEFAULT_CHECKS:
            all_ok = False
        ok_count += default_ok
        # Run 2: piped-stdin end-to-end ic_readline check (1 assertion).
        # stdin is a pipe with data then EOF, so isocline takes its
        # documented direct-read fallback instead of terminal editing.
        stdin_out, stdin_rc = self._run_capture(
            [bin_path, "--stdin-line"], stdin_text="hello isocline\n")
        stdin_ok = stdin_out.count("CHECK-OK:")
        self.output.info(stdin_out[-2000:])
        if stdin_rc != 0 or stdin_ok != EXPECTED_STDIN_CHECKS:
            all_ok = False
        ok_count += stdin_ok
        marker = {
            "executed": True,
            "passed": all_ok and ok_count == CONSUMER_CHECK_COUNT,
            "command": '"test_isocline" + "test_isocline --stdin-line < piped line"',
            "discovered": CONSUMER_CHECK_COUNT,
            "passedCount": ok_count,
        }
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
        )
        if not marker["passed"] and raise_on_failure:
            raise ConanException(
                "consumer test failed: ok=%s/%s" % (ok_count, CONSUMER_CHECK_COUNT)
            )

    def _run_capture(self, argv, stdin_text=None):
        proc = subprocess.run(
            argv,
            input=stdin_text,
            env=dict(os.environ),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=300,
        )
        return proc.stdout or "", proc.returncode
