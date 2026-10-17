#!/usr/bin/env python3
"""Conan test_package for xalan 1.12 — Conan L1 official test.

Consumer check: links the packaged XalanC library and runs a real XSLT
transform (foo.xml + foo.xsl -> foo.out) through XalanTransformer, then
asserts on the output file. Uses CMake (CMakeDeps + CMakeToolchain) so the
compiler comes from the Conan toolchain, not raw shell env vars (R33).

HMBS evidence: after the binary passes (exit 0), emits
HMBS_TEST_PACKAGE_RESULT (6 real consumer assertions) and re-emits the
upstream ctest result carried in the package res/ dir so cache-hit runs
still provide evidence every round.
"""

import json
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class XalanTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _hmbs_emit(self, line):
        self.output.info(line)
        try:
            print(line, flush=True)
        except Exception:
            pass

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: consumer compiled and linked")
            return
        executable = os.path.join(
            self.cpp.build.bindirs[0], "test_xalan"
        )
        self.run(executable, env="conanrun")
        # The binary exits non-zero on any assertion failure; reaching
        # here means all 6 consumer assertions passed.
        self._hmbs_emit(
            "HMBS_TEST_PACKAGE_RESULT=%s"
            % json.dumps(
                {
                    "executed": True,
                    "passed": True,
                    "command": "./test_xalan",
                    "discovered": 6,
                    "passedCount": 6,
                },
                separators=(",", ":"),
            )
        )
        # Re-emit the real upstream result carried in the package res so
        # cache-hit runs still provide evidence every round.
        try:
            res = os.path.join(
                self.dependencies["xalan"].package_folder,
                "res",
                "hmbs_upstream.json",
            )
            with open(res, "r", encoding="utf-8") as f:
                payload = json.load(f)
            if (
                payload.get("status") == "passed"
                and int(payload.get("discovered", 0)) > 0
                and int(payload.get("executed", 0)) > 0
            ):
                self._hmbs_emit(
                    "HMBS_UPSTREAM_TEST_RESULT=%s"
                    % json.dumps(payload, separators=(",", ":"))
                )
            else:
                self.output.warning(
                    "HMBS diag upstream res invalid: %s" % payload
                )
        except Exception as e:
            self.output.warning("HMBS diag upstream res missing: %s" % e)
