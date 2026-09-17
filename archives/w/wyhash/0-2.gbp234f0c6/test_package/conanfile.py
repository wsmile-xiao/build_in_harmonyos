#!/usr/bin/env python3
"""Conan test_package for wyhash 0-2.gbp234f0c6 — consumer layer.

test_wyhash.cpp includes <wyhash.h> through the installed CMake target and
checks the official upstream hash vectors plus the public utility API
(R34: the test really uses the package).  The upstream test_vector.cpp run
lives in the recipe build() step (layer 1).
"""
import json
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class WyhashTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        # CMake on OHOS has no Platform/HarmonyOS.cmake; reuse the Linux
        # platform logic together with the aarch64 processor.
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

    def _bash(self):
        for candidate in (
            os.environ.get("CONFIG_SHELL"),
            shutil.which("bash"),
            "/storage/Users/currentUser/.harmonybrew/bin/bash",
            "/data/service/hnp/bin/bash",
            "/bin/bash",
        ):
            if candidate and os.path.isfile(candidate):
                return candidate
        return "bash"

    def _run_binary(self, binary):
        """Run a freshly built ELF, tolerating OHOS sh exec limitations."""
        direct = shlex.quote(binary)
        if self.settings.os == "OHOS":
            bash = self._bash()
            wrapped = f"{shlex.quote(bash)} -c {shlex.quote(direct)}"
            rc = self.run(wrapped, env="conanrun", ignore_errors=True)
            if rc == 0:
                return rc
        return self.run(direct, env="conanrun", ignore_errors=True)

    def test(self):
        binary = os.path.join(self.cpp.build.bindirs[0], "test_wyhash")
        rc = self._run_binary(binary)
        passed = (rc == 0)
        print("\nHMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": passed,
            "command": "test_wyhash",
        }))
        if not passed:
            raise ConanException(f"consumer test failed, rc={rc}")
