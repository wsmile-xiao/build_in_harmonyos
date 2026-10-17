#!/usr/bin/env python3
"""Conan test_package for qpid-proton 0.38.0 — CI L1 consumer test.

Builds test_qpid_proton against the *installed* package (find_package(Proton)
-> Proton::qpid-proton) and runs it on the HarmonyOS PC target.  The program
performs 13 checks and prints one "CHECK-OK: <group>/<name>" line per check
(6 platform checks, 7 consumer checks).  The per-check lines are counted here so
that a stub binary which exits 0 without doing anything cannot pass, and so the
platform/consumer split is available as machine evidence for the PR statistics.
"""

import json
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout

CONSUMER_CHECK_COUNT = 13
PLATFORM_CHECK_COUNT = 6
CONSUMER_BIN_NAME = "test_qpid_proton"


class QpidProtonTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _consumer_binary(self):
        for directory in self.cpp.build.bindirs:
            candidate = os.path.join(directory, CONSUMER_BIN_NAME)
            if os.path.isfile(candidate):
                return candidate
        for root, _, files in os.walk(self.build_folder):
            if CONSUMER_BIN_NAME in files:
                return os.path.join(root, CONSUMER_BIN_NAME)
        return None

    def test(self):
        binary = self._consumer_binary()
        if binary is None:
            raise ConanException("consumer binary %s was not built"
                                 % CONSUMER_BIN_NAME)
        # L0 gate requires an explicit, real self.run() inside test().
        self.run(binary, env="conanrun")

        # Machine evidence: run once more with the package lib directory on
        # LD_LIBRARY_PATH and count the per-check lines.
        run_env = dict(os.environ)
        try:
            dep = self.dependencies[self.tested_reference_str]
            run_env["LD_LIBRARY_PATH"] = "%s:%s" % (
                os.path.join(dep.package_folder, "lib"),
                run_env.get("LD_LIBRARY_PATH", ""))
        except Exception:  # pragma: no cover - dependency always present here
            pass
        proc = subprocess.run([binary], env=run_env, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True, timeout=300)
        output = proc.stdout or ""
        self.output.info(output)
        ok_lines = [ln for ln in output.splitlines()
                    if ln.startswith("CHECK-OK:")]
        platform_ok = [ln for ln in ok_lines if "platform/" in ln]
        marker = {
            "executed": True,
            "passed": proc.returncode == 0 and len(ok_lines) == CONSUMER_CHECK_COUNT,
            "return_code": proc.returncode,
            "discovered": CONSUMER_CHECK_COUNT,
            "passedCount": len(ok_lines),
            "platformChecksDiscovered": PLATFORM_CHECK_COUNT,
            "platformChecksPassed": len(platform_ok),
            "consumerChecksPassed": len(ok_lines) - len(platform_ok),
        }
        print("QPID_PROTON_TEST_PACKAGE_RESULT=" + json.dumps(marker), flush=True)
        self.output.info("QPID_PROTON_TEST_PACKAGE_RESULT=" + json.dumps(marker))
        if not marker["passed"]:
            raise ConanException("consumer test failed: rc=%s checks=%s/%s"
                                 % (proc.returncode, len(ok_lines),
                                    CONSUMER_CHECK_COUNT))
        self.output.info("qpid-proton consumer test_package passed (%s checks)"
                         % len(ok_lines))
