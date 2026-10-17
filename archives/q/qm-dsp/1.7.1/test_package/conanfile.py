#!/usr/bin/env python3
"""Conan test_package for qm-dsp 1.7.1 — consumer round-trip test.

Builds test_qmdsp.cpp against the packaged static library and runs four
real DSP assertions (Pitch, FFT, MathUtilities, MedianFilter). Parses the
CASE PASS lines for the HMBS_TEST_PACKAGE_RESULT marker, then re-emits the
upstream evidence persisted by the recipe build (no hardcoded copies).
"""

import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import replace_in_file


class QmDspTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # Same dead-absolute-path guard as the main recipe: the profile
        # points at /data/service/hnp/bin/clang{,++} which may be absent
        # on the true device; override only when the configured path is
        # unusable and PATH offers a working compiler. cache_variables
        # alone does not move the baked compiler line in
        # conan_toolchain.cmake, so the file is patched after generate()
        # (bzrtp/5.3.105 precedent: cache_variables + post-generate patch).
        executables = self.conf.get("tools.build:compiler_executables",
                                    default={}, check_type=dict) or {}
        for key, cmake_var, fallback in (("c", "CMAKE_C_COMPILER", "clang"),
                                         ("cpp", "CMAKE_CXX_COMPILER", "clang++")):
            configured = executables.get(key)
            if configured and os.path.isabs(configured):
                if not (os.path.isfile(configured)
                        and os.access(configured, os.X_OK)):
                    found = shutil.which(fallback)
                    if found:
                        self.output.warning(
                            f"test_package compiler unavailable: {configured},"
                            f" use {found}")
                        tc.cache_variables[cmake_var] = found
        tc.generate()
        self._patch_cmake_toolchain_compilers()
        CMakeDeps(self).generate()

    def _compiler_executable(self, key, fallback_name):
        executables = self.conf.get("tools.build:compiler_executables",
                                    default={}, check_type=dict) or {}
        configured = executables.get(key)
        if configured and os.path.isfile(configured) \
                and os.access(configured, os.X_OK):
            return configured
        found = shutil.which(fallback_name)
        return found or configured or fallback_name

    def _patch_cmake_toolchain_compilers(self):
        toolchain = os.path.join(self.generators_folder,
                                 "conan_toolchain.cmake")
        replacements = {
            "/data/service/hnp/bin/clang++":
                self._compiler_executable("cpp", "clang++"),
            "/data/service/hnp/bin/clang":
                self._compiler_executable("c", "clang"),
        }
        for old, new in replacements.items():
            replace_in_file(self, toolchain, old, new, strict=False)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: skip runtime test")
            return
        binary = os.path.join(self.cpp.build.bindirs[0], "test_qmdsp")
        log_path = os.path.join(self.build_folder, "test_qmdsp.log")
        try:
            self.run(f'"{binary}" > "{log_path}" 2>&1', env="conanrun")
        except ConanException:
            pass
        out = ""
        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                out = f.read()
        except OSError:
            out = ""
        self.output.info("test output:\n" + out)
        discovered = 4
        passed_count = out.count("CASE PASS")
        marker = {
            "executed": True,
            "passed": discovered > 0 and passed_count == discovered,
            "command": "./test_qmdsp (Pitch + FFT + MathUtilities + MedianFilter)",
            "discovered": discovered,
            "passedCount": passed_count,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
        self._emit_upstream_result()
        if not marker["passed"]:
            raise ConanException(
                f"test_package failed: {passed_count}/{discovered} cases passed"
            )

    def _emit_upstream_result(self):
        dep = self.dependencies["qm-dsp"]
        path = os.path.join(dep.package_folder, "res", "upstream_test_result.json")
        if not os.path.isfile(path):
            raise ConanException("upstream_test_result.json not found in package")
        with open(path, "r", encoding="utf-8") as f:
            result = json.load(f)
        ok_shape = (
            isinstance(result, dict)
            and result.get("status") == "passed"
            and int(result.get("discovered", 0)) == 64
            and int(result.get("executed", 0)) == 64
            and int(result.get("passed", 0)) == 64
            and int(result.get("failed", 0)) == 0
            and int(result.get("skipped", 0)) == 0
        )
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result))
        if not ok_shape:
            raise ConanException(f"upstream test evidence invalid: {result}")
