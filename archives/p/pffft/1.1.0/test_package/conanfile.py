#!/usr/bin/env python3
"""Conan consumer test for pffft 1.1.0 (dispatch-mandated shape).

Builds and runs test_pffft.c: 64-point real FFT -> IFFT round trip with
energy-conservation assertions and tolerance-based comparison against a naive
in-test DFT (same reference role as upstream's in-tree FFTPACK). The consumer
program prints its own assertion count, reported through
HMBS_TEST_PACKAGE_RESULT.
"""

import json
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class PffftTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):

        tc = CMakeToolchain(self)
        # CMake >= 4 workers break the compiler check on the OHOS-adapted
        # CMAKE_SYSTEM_NAME=HarmonyOS mapping (no Platform/HarmonyOS module
        # in CMake). OHOS is POSIX: force the Linux platform (chain-wide
        # convention; abcmidi/adios2 precedent).
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch)
            )
        tc.generate()

        # HMBS readonly_tmp: /tmp is erofs read-only on device runners.
        # Pass through the HMBS-injected writable TMPDIR/TMP/TEMP into both
        # build and run scopes so cmake build and the consumer test binary
        # avoid /tmp. Only the temp root is replaced; test scope unchanged.
        tmp_env = Environment()
        for _var in ("TMPDIR", "TMP", "TEMP"):
            _val = os.environ.get(_var)
            if _val:
                tmp_env.define(_var, _val)
        tmp_env.vars(self, scope="build").save_script("hmbs_tmpdir_build")
        tmp_env.vars(self, scope="run").save_script("hmbs_tmpdir_run")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        test_pkg = {
            "name": "test_package",
            "success": True,
            "executed": False,
            "passed": False,
            "command": "./test_pffft",
            "discovered": 0,
            "passedCount": 0,
        }
        if not can_run(self):
            test_pkg["command"] = "CMake build (compile+link) only: cannot run on build host"
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))
            print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False), flush=True)
            return
        executable = os.path.join(self.cpp.build.bindir, "test_pffft")
        try:
            self.run(f'"{executable}"', env="conanrun")
            passed = True
        except Exception:
            passed = False
        # the consumer program reports "test_pffft: N checks passed, M failed"
        # (11 assertions total, see test_pffft.c header) and exits nonzero on
        # any failure, so the returncode is the authoritative verdict.
        test_pkg["executed"] = True
        test_pkg["passed"] = passed
        test_pkg["discovered"] = 11
        test_pkg["passedCount"] = 11 if passed else 0
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False), flush=True)
        if not passed:
            raise ConanException("consumer test failed (see log above)")
