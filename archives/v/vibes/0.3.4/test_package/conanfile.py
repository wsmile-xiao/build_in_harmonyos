#!/usr/bin/env python3
"""Conan test_package — vibes 0.3.4 consumer test.

Builds test_vibes.cpp against the packaged libvibes (CMakeDeps +
CMakeToolchain) and runs it on the native OHOS target, counting the
per-check "CHECK-OK:" lines for the HMBS_TEST_PACKAGE_RESULT
machine-evidence marker (exit-0 alone is not proof: all discovered
checks must print CHECK-OK).

Upstream evidence: the VIBES C++ client API 0.3.4 ships no automated
test harness (see test_package/MANIFEST.yml audit), so this re-emits
HMBS_UPSTREAM_TEST_RESULT with status=no_tests on every run (cache-hit
rounds skip the main build, the gate still needs the marker).
"""

import json
import os
import shutil

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout

# test_vibes.cpp performs exactly 13 checks, one "CHECK-OK: <name>" line each.
CONSUMER_CHECK_COUNT = 13


class VibesTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def _resolve_tool_compiler(self, kind):
        # Mirror of the main recipe: prefer the profile-pinned
        # tools.build:compiler_executables path; if it is absent on a
        # given runner, fall back to PATH discovery.
        try:
            configured = self.conf.get(
                "tools.build:compiler_executables:%s" % kind, check_type=str)
        except Exception:
            configured = None
        if configured:
            if os.path.exists(configured):
                return configured
            base = os.path.basename(configured)
            for cand in ([base] + (["clang", "cc"] if kind == "c"
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
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_C_COMPILER"] = self._resolve_tool_compiler("c")
        tc.variables["CMAKE_CXX_COMPILER"] = self._resolve_tool_compiler("cpp")
        tc.generate()

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self, build_folder="$TMP")

    def _ensure_writable_tmp(self):
        # [readonly_tmp]: /tmp may be read-only on the device. Prefer the
        # HMBS-injected TMPDIR/TMP/TEMP; fall back to a dir under the build
        # folder.
        for key in ("TMPDIR", "TMP", "TEMP"):
            candidate = os.environ.get(key)
            if candidate and os.path.isdir(candidate):
                try:
                    probe = os.path.join(candidate, ".hmbs_write_probe")
                    with open(probe, "w") as handle:
                        handle.write("ok")
                    os.remove(probe)
                    return candidate
                except OSError:
                    continue
        fallback = os.path.join(self.build_folder, "hmbs-tmp")
        os.makedirs(fallback, exist_ok=True)
        return fallback

    def build(self):
        tmp = self._ensure_writable_tmp()
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmp
        os.environ["CC"] = self._resolve_tool_compiler("c")
        os.environ["CXX"] = self._resolve_tool_compiler("cpp")
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _emit_upstream_marker(self):
        marker = {
            "status": "no_tests",
            "framework": "none",
            "command": "no upstream test target (see test_package/MANIFEST.yml audit)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "VIBES C++ client API 0.3.4 ships no automated test suite: "
                "no TEST/ctest wiring, no make check target and no "
                "build-system test hook (client-api/C++ holds only src/ "
                "vibes.h+vibes.cpp and examples/ demo programs with no "
                "assertions); the Qt viewer's tests/ folder holds a JSON "
                "fixture, not an executable test runner, and the viewer "
                "itself is a Qt GUI app not built for OHOS; "
                "see test_package/MANIFEST.yml upstream_test_audit"
            ),
        }
        line = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False)
        self.output.info(line)
        print(line, flush=True)

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile/link test completed")
            self._emit_upstream_marker()
            return
        tmp = self._ensure_writable_tmp()
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmp
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_vibes")
        if not os.path.isfile(bin_path):
            raise RuntimeError("test binary missing: %s" % bin_path)
        # Run from a writable cwd so test_vibes.json is created there.
        run_dir = os.path.dirname(bin_path)
        # Execute the real test program via Conan self.run() (native shell,
        # inherits the process environment). Redirect harness stdout to a
        # deterministic log file which is the single source for the marker
        # counts (no arithmetic on captured output).
        log_path = os.path.join(tmp, "test_vibes_out.log")
        rc = self.run('"%s" > "%s" 2>&1' % (bin_path, log_path), cwd=run_dir)
        out = ""
        if os.path.isfile(log_path):
            with open(log_path, "r", encoding="utf-8",
                      errors="replace") as handle:
                out = handle.read()
        self.output.info(out[-3000:])
        ok_count = out.count("CHECK-OK:")
        failed_count = out.count("CHECK-FAIL:")
        passed = (rc == 0
                  and ok_count == CONSUMER_CHECK_COUNT
                  and failed_count == 0)
        marker = {
            "executed": True,
            "passed": passed,
            "command": bin_path,
            "discovered": CONSUMER_CHECK_COUNT,
            "passedCount": ok_count,
        }
        line = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
        self.output.info(line)
        print(line, flush=True)
        # Upstream evidence (no_tests) re-emission for the hmbs gate.
        self._emit_upstream_marker()
        if not passed:
            raise RuntimeError(
                "consumer test failed: rc=%s ok=%s/%s fail=%s"
                % (rc, ok_count, CONSUMER_CHECK_COUNT, failed_count))
        self.output.info("vibes consumer test_package passed")
