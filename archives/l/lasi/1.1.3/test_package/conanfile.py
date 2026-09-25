#!/usr/bin/env python3
"""Conan consumer tests for libLASi."""

import json
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LasiTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        if str(self.settings.os) == "OHOS":
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["CMAKE_CXX_STANDARD"] = 17
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = True
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            self.output.warning("cross-building: target runtime tests skipped")
            return

        bindir = os.path.join(self.build_folder, "bin")
        commands = [("test_lasi", "portable consumer API test")]
        if str(self.settings.os) == "OHOS":
            commands.append(("test_lasi_ohos", "HarmonyOS runtime/font test"))

        passed = 0
        error = None
        for executable, label in commands:
            path = os.path.join(bindir, executable)
            try:
                self.run('"%s"' % path, env="conanrun")
                passed += 1
            except Exception as exc:
                self.output.error("%s failed: %s" % (label, exc))
                error = exc
                break

        result = {
            "executed": True,
            "passed": error is None and passed == len(commands),
            "command": " + ".join(item[0] for item in commands),
            "discovered": len(commands),
            "passedCount": passed,
        }
        marker = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(result)
        print(marker, flush=True)
        self.output.info(marker)
        if error is not None or passed != len(commands):
            raise ConanException(
                "LASi consumer tests failed: %d/%d passed"
                % (passed, len(commands))
            )
