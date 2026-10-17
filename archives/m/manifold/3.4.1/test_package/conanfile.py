#!/usr/bin/env python3
"""test_package for manifold/3.4.1.

Builds a small C++ consumer that constructs Cube/Sphere/CrossSection through
the public manifold API and asserts their validity, then runs it via
self.run() (real execution). Emits HMBS_TEST_PACKAGE_RESULT for the consumer
case and re-emits the real upstream ctest result persisted in the package res/
dir so cache-hit runs still provide machine evidence.
"""

import json
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class ManifoldTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()
        CMakeDeps(self).generate()
        VirtualRunEnv(self).generate()

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
        if cross_building(self):
            self.output.info("cross-building: consumer compiled and linked")
            return
        # Run the real consumer binary; self.run() raises on non-zero exit
        # (any assertion failure propagates as a failed test).
        executable = os.path.join(self.cpp.build.bindirs[0], "test_manifold")
        self.run(executable, env="conanrun")
        # One real test case (test_manifold binary, 5 assertions inside).
        self._hmbs_emit("HMBS_TEST_PACKAGE_RESULT=%s" % json.dumps(
            {"executed": True, "passed": True,
             "command": "./test_manifold",
             "discovered": 1, "passedCount": 1},
            separators=(",", ":")))
        # Re-emit the real upstream result carried in the package res/ so
        # cache-hit test_package runs still produce upstream evidence.
        try:
            res = os.path.join(self.dependencies["manifold"].package_folder,
                               "res", "hmbs_upstream.json")
            with open(res, "r", encoding="utf-8") as f:
                payload = json.load(f)
            if payload.get("status") == "passed" and \
                    int(payload.get("discovered", 0)) > 0 and \
                    int(payload.get("executed", 0)) > 0:
                self._hmbs_emit("HMBS_UPSTREAM_TEST_RESULT=%s" % json.dumps(
                    payload, separators=(",", ":")))
            else:
                self.output.warning(
                    "HMBS diag upstream res invalid: %s" % payload)
        except Exception as e:
            self.output.warning(
                "HMBS diag upstream res missing: %s" % e)
