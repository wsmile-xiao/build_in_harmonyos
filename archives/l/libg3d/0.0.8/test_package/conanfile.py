#!/usr/bin/env python3
"""Conan test_package — libg3d 0.0.8 (Conan L1 official test).

Consumer test (test_libg3d.c) exercises context, material, primitive,
object and model APIs with 12 check() assertions (any failure flips the
exit code to 1, so rc 0 proves all 12 passed). Machine evidence (HMBS
preflight hard gate):
- HMBS_TEST_PACKAGE_RESULT with the real consumer-test counters.
- HMBS_UPSTREAM_TEST_RESULT re-emitted from the verdict recorded by the
  main recipe build() (package file hmbs_upstream_result.json), so the
  evidence survives Conan cache hits where build() is skipped.
Both markers are emitted dual-channel (raw print + self.output.info):
HMBS preflight scrapes raw stdout, so info-only emits are missed.
Failure paths emit failed markers BEFORE raising, so a consumer failure
or missing verdict file never surfaces as missing evidence.
"""

import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout


class Libg3dTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        self._patch_toolchain_compiler()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _patch_toolchain_compiler(self):
        # Preflight 2026-09-20: CMake configure fails with
        #   "System is unknown to cmake, create: Platform/HarmonyOS" +
        #   "The CMAKE_C_COMPILER: /data/service/hnp/bin/clang ... errors".
        # The unknown-platform notice itself is warning-level for POSIX C
        # libs (E092/NNG precedent); the fatal part is the profile-hardcoded
        # absolute compiler which is inaccessible from the preflight sandbox
        # (same root cause as the main-recipe /bin/sh + PATH-resolved clang
        # fix, and the lz4/dr_flac precedent). Patch the generated toolchain
        # file to the PATH-resolved working compiler. No-op when the profile
        # path already executes (real CI).
        try:
            gen = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        except Exception:
            return
        try:
            if not os.path.isfile(gen):
                return
            with open(gen, "r", encoding="utf-8", errors="replace") as handle:
                text = handle.read()
        except OSError:
            return
        replacements = {}
        for name in ("clang", "clang++"):
            resolved = shutil.which(name)
            if not resolved or not os.path.isfile(resolved):
                continue
            try:
                probe = subprocess.run(
                    [resolved, "--version"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=10,
                )
            except Exception:
                continue
            if probe.returncode != 0:
                continue
            for hard in ("/data/service/hnp/bin/" + name,):
                if hard in text and hard != resolved:
                    replacements[hard] = resolved
        if not replacements:
            return
        for hard, resolved in replacements.items():
            text = text.replace(hard, resolved)
        try:
            with open(gen, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(text)
        except OSError:
            return
        self.output.info("patched test_package toolchain compiler: {}".format(replacements))

    def _emit(self, name, payload):
        marker = name + "=" + json.dumps(payload, ensure_ascii=False)
        print(marker, flush=True)
        self.output.info(marker)

    def test(self):
        consumer_ok = True
        try:
            self.run(os.path.join(self.cpp.build.bindir, "test_libg3d"), env="conanrun")
        except Exception:
            consumer_ok = False
        marker = {
            "executed": True,
            "passed": consumer_ok,
            "command": "./test_libg3d (12 context/material/primitive/object/model API assertions)",
            "discovered": 12,
            "passedCount": 12 if consumer_ok else 0,
        }
        self._emit("HMBS_TEST_PACKAGE_RESULT", marker)

        dep = self.dependencies["libg3d"]
        marker_file = os.path.join(str(dep.package_folder), "hmbs_upstream_result.json")
        upstream_marker = None
        upstream_ok = False
        if os.path.isfile(marker_file):
            try:
                with open(marker_file, encoding="utf-8") as handle:
                    data = json.load(handle)
                upstream_marker = {k: data.get(k) for k in
                                   ("status", "framework", "command", "discovered",
                                    "executed", "passed", "failed", "skipped")}
                if data.get("reason"):
                    upstream_marker["reason"] = data.get("reason")
                upstream_ok = (data.get("status") in ("passed", "no_tests")
                               and (data.get("status") == "no_tests" or bool(data.get("executed"))))
            except (OSError, ValueError) as exc:
                upstream_marker = {
                    "status": "failed",
                    "framework": "autotools-check",
                    "command": "read hmbs_upstream_result.json",
                    "discovered": 4,
                    "executed": 0,
                    "passed": 0,
                    "failed": 0,
                    "skipped": 0,
                    "reason": "verdict file unreadable: {}: {}".format(marker_file, exc),
                }
        else:
            upstream_marker = {
                "status": "failed",
                "framework": "autotools-check",
                "command": "read hmbs_upstream_result.json",
                "discovered": 4,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "upstream test verdict missing: {} (recipe build() must run the suite)".format(marker_file),
            }
        self._emit("HMBS_UPSTREAM_TEST_RESULT", upstream_marker)
        if not consumer_ok:
            raise ConanException("consumer test test_libg3d failed (see HMBS_TEST_PACKAGE_RESULT)")
        if not upstream_ok:
            raise ConanException("upstream suite did not pass: {}".format(upstream_marker))
        self.output.info("test libg3d consumer + upstream evidence OK")
