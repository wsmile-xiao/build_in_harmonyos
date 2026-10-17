#!/usr/bin/env python3
"""Conan test_package — cyrus-sasl-digestmd5 2.1.28 consumer test.

Builds test_digestmd5.c against the packaged libsasl2 with DIGEST-MD5
support (CMakeDeps + CMakeToolchain), runs it on the native OHOS target
and counts the per-check "CHECK-OK:" lines for the
HMBS_TEST_PACKAGE_RESULT machine-evidence marker (exit-0-alone is not
proof: 8 CHECK-OK lines are required for a pass, two of them
OHOS-specific: static mechanism table without any dlopen plugin
directory, and the OpenSSL DES provider behind the DIGEST-MD5
confidentiality layer).

Upstream evidence: cyrus-sasl 2.1.28 registers no automated test target
(no make check TESTS/check_PROGRAMS anywhere; audit in MANIFEST.yml),
but it does ship utils/testsuite.c — a self-contained assertion harness
that the recipe drives during build(); its counters are persisted into
the package as res/hmbs_upstream.json and re-emitted here so cache-hit
rounds still carry the upstream evidence marker.
"""

import json
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.cmake import CMake
from conan.tools.cmake import cmake_layout

# test_digestmd5.c performs exactly 8 checks, each printing one
# "CHECK-OK: <name>" line on success.
CONSUMER_CHECK_COUNT = 8


class Cyrussasldigestmd5TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _ensure_writable_tmp(self):
        # HMBS injects a task-private writable TMPDIR on the real machine
        # (/tmp is read-only: [readonly_tmp]). Prefer it in every phase;
        # fall back to a dir under build_folder so neither CMake/ctest nor
        # the test binary ever touches /tmp.
        tmp = None
        for key in ("TMPDIR", "TMP", "TEMP"):
            candidate = os.environ.get(key)
            if candidate and os.path.isdir(candidate):
                tmp = candidate
                break
        if not tmp:
            tmp = os.path.join(self.build_folder, "hmbs-tmp")
            os.makedirs(tmp, exist_ok=True)
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmp
        # The consumer binary links the OpenSSL DES provider (transitively
        # via the package's cpp_info.requires); make its libraries
        # resolvable for every child process below (ctest and the direct
        # binary run), independent of the conanrun environment plumbing.
        libdirs = []
        for _dep in self.dependencies.values():
            try:
                _folder = str(_dep.package_folder)
            except Exception:
                continue
            _libdir = os.path.join(_folder, "lib")
            if os.path.isdir(_libdir):
                libdirs.append(_libdir)
        if libdirs:
            old_ld = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = (
                os.pathsep.join(libdirs)
                + (os.pathsep + old_ld if old_ld else ""))
        return tmp

    def _package_folder(self):
        try:
            return str(self.dependencies[self.tested_reference_str]
                       .package_folder)
        except Exception:
            try:
                return str(self.dependencies["cyrus-sasl-digestmd5"]
                           .package_folder)
            except Exception:
                return ""

    def build(self):
        # Keep CMake temp files off a possibly read-only /tmp.
        self._ensure_writable_tmp()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _emit_upstream_marker(self):
        # Re-emit the upstream harness counters persisted by the recipe
        # (package/res/hmbs_upstream.json) so cache-hit rounds keep the
        # evidence marker. Fall back to MANIFEST.yml's declared counts.
        marker = None
        pkg = self._package_folder()
        if pkg:
            path = os.path.join(pkg, "res", "hmbs_upstream.json")
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    marker = json.load(handle)
            except (OSError, ValueError):
                marker = None
        if marker is None:
            marker = {
                "status": "no_automated_suite",
                "framework": "autotools-make-check",
                "command": "make check (upstream registers no automated tests)",
                "discovered": 0,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": (
                    "cyrus-sasl 2.1.28 registers no automated test target: "
                    "no automake TESTS/check_PROGRAMS, no ctest/meson/pytest "
                    "wiring, and utils/testsuite.c is an EXTRA_PROGRAM "
                    "(manual harness, not a make check target); "
                    "see test_package/MANIFEST.yml upstream_test_audit"
                ),
            }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT="
            + json.dumps(marker, ensure_ascii=False)
        )

    def _dump_last_test_log(self):
        # ctest writes per-test output to Testing/Temporary/LastTest.log
        # under the build dir; surface it so the next preflight round can
        # see the real test_digestmd5 failure without guessing.
        try:
            candidates = []
            build_folder = getattr(self, "build_folder", "") or ""
            if build_folder and os.path.isdir(build_folder):
                for root, dirs, files in os.walk(build_folder):
                    if "LastTest.log" in files:
                        candidates.append(os.path.join(root, "LastTest.log"))
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
            self._run_consumer_binary(raise_on_failure=False)
            self._emit_upstream_marker()
            raise
        self._run_consumer_binary(raise_on_failure=True)
        # L0d quality gate: prove the binary also executes under the
        # conanrun environment (uses the same writable TMPDIR).
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_digestmd5")
        self.run(bin_path, env="conanrun")
        self._emit_upstream_marker()
        self.output.info("cyrus-sasl-digestmd5 consumer test_package passed")

    def _log_package_libs_for_ohos(self):
        # Diagnose static-vs-shared mixups: the default package must ship
        # libsasl2.a (shared=False) while the shared option ships
        # libsasl2.so plus lib/sasl2/libdigestmd5.so. Log the libdir so the
        # next preflight shows a stale .so DT_NEEDED risk directly.
        pkg = self._package_folder()
        if not pkg:
            return
        libdir = os.path.join(pkg, "lib")
        try:
            names = sorted(os.listdir(libdir))
        except OSError as exc:
            self.output.info("package libdir missing %s: %s" % (libdir, exc))
            return
        self.output.info("package libdir %s: %s" % (libdir, ", ".join(names)))
        plugindir = os.path.join(libdir, "sasl2")
        if os.path.isdir(plugindir):
            try:
                plugins = sorted(os.listdir(plugindir))
            except OSError:
                plugins = []
            self.output.info("package plugindir %s: %s"
                             % (plugindir, ", ".join(plugins)))

    def _run_consumer_binary(self, raise_on_failure):
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_digestmd5")
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
