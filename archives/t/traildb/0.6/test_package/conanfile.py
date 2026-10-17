#!/usr/bin/env python3
"""Conan test_package for traildb 0.6 — exercises the real public API.

Builds test_traildb.c (cons open/add/finalize, open, trails, cursor)
with CMake, runs it via ctest plus a direct binary run, and counts the
per-check "PASS N:" lines for the HMBS_TEST_PACKAGE_RESULT
machine-evidence marker (exit-0-alone is not proof: 7 PASS lines are
required for a pass; single deterministic source, no returncode patch-up).
"""

import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout

# test_traildb.c prints exactly one "PASS N:" line per check (1..7).
CONSUMER_CHECK_COUNT = 7


class TraildbTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # True device migrated clang from /data/service/hnp/bin to
        # ~/usr/local/bin while the shared profile still points at the old
        # path; pin the real compiler so conan_toolchain.cmake does not
        # reference the missing tool (same fix as zydis/4.1.1).
        toolchain = CMakeToolchain(self)
        try:
            compilers = self.conf.get("tools.build:compiler_executables",
                                       default=None)
        except Exception:
            compilers = None
        if not isinstance(compilers, dict):
            compilers = {}
        configured = compilers.get("c")
        resolved = None
        if configured and os.path.isfile(configured):
            resolved = configured
        if resolved is None:
            resolved = shutil.which("clang") or shutil.which("cc")
        if resolved is None:
            home_bin = os.path.join(os.path.expanduser("~"), "usr",
                                    "local", "bin")
            for name in ("clang", "cc"):
                cand = os.path.join(home_bin, name)
                if os.path.isfile(cand):
                    resolved = cand
                    break
        if resolved:
            toolchain.cache_variables["CMAKE_C_COMPILER"] = resolved
        self.output.info("HMBS diag test_package c=%s resolved=%s"
                         % (configured, resolved))
        toolchain.generate()
        # CMakeToolchain cache pin may not override the stale profile value
        # in the generated file (zydis/4.1.1 evidence 2026-09-18), so patch
        # the artifact itself when the configured path is missing.
        if configured and resolved and configured != resolved \
                and not os.path.isfile(configured) \
                and os.path.isfile(resolved):
            try:
                path = os.path.join(self.generators_folder,
                                    "conan_toolchain.cmake")
                if os.path.isfile(path):
                    with open(path, "r", encoding="utf-8",
                              errors="replace") as f:
                        text = f.read()
                    new_text = text.replace(configured, resolved)
                    if new_text != text:
                        with open(path, "w", encoding="utf-8") as f:
                            f.write(new_text)
                        self.output.info("HMBS diag fixed generated toolchain")
            except Exception as e:
                self.output.warning("HMBS diag toolchain fix failed: %s" % e)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _emit(self, line):
        self.output.info(line)
        try:
            print(line, flush=True)
        except Exception:
            pass

    def _find_test_binary(self):
        names = ("test_traildb", "test_traildb.exe")
        try:
            direct = os.path.join(self.cpp.build.bindirs[0], "test_traildb")
            if os.path.isfile(direct):
                return direct
        except Exception:
            pass
        hits = []
        base = getattr(self, "build_folder", "") or ""
        if base and os.path.isdir(base):
            for root, _dirs, files in os.walk(base):
                for name in names:
                    if name in files:
                        hits.append(os.path.join(root, name))
        if not hits:
            raise ConanException(
                "test_traildb binary not found under build folder %s" % base)
        hits.sort(key=len)
        self.output.info("test binary: %s" % hits[0])
        return hits[0]

    def _dump_last_test_log(self):
        try:
            base = getattr(self, "build_folder", "") or ""
            if not (base and os.path.isdir(base)):
                return
            candidates = []
            for root, dirs, files in os.walk(base):
                if "LastTest.log" in files:
                    candidates.append(os.path.join(root, "LastTest.log"))
                if root.count(os.sep) - base.count(os.sep) > 6:
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
            self.output.info("cross-building: consumer compiled and linked")
            return
        # L1 evidence: run the registered ctest (no shell wrapper; the
        # profile hnp bash is inaccessible in HMDFS build dirs).
        ctest_ok = True
        try:
            self.run("ctest --output-on-failure", env="conanrun")
        except Exception as exc:
            ctest_ok = False
            self.output.warning("ctest failed: %s" % exc)
            self._dump_last_test_log()
        # Deterministic counting source: run the consumer binary directly
        # and count one anchored "PASS N:" line per check. Both channels
        # (print + output.info) carry the marker every run.
        bin_path = self._find_test_binary()
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
        # Single source: anchored per-check lines, independent counters.
        passed = len(re.findall(r"^PASS \d+:", output, re.MULTILINE))
        failed = len(re.findall(r"^FAIL \d+", output, re.MULTILINE))
        ok = (ctest_ok and proc.returncode == 0
              and passed == CONSUMER_CHECK_COUNT and failed == 0)
        marker = {
            "executed": True,
            "passed": ok,
            "command": "ctest --output-on-failure",
            "discovered": CONSUMER_CHECK_COUNT,
            "passedCount": passed,
        }
        self._emit("HMBS_TEST_PACKAGE_RESULT="
                   + json.dumps(marker, ensure_ascii=False))
        if not ok:
            raise ConanException(
                "consumer test failed: ctest_ok=%s rc=%s passed=%s/%s failed=%s"
                % (ctest_ok, proc.returncode, passed,
                   CONSUMER_CHECK_COUNT, failed))
        self.output.info("traildb consumer test_package passed (7/7)")
