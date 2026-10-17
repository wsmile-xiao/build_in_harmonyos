#!/usr/bin/env python3
"""Conan test_package — libspctag 0.2 consumer and OHOS tests."""

import json
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibspctagTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        toolchain = CMakeToolchain(self)
        if str(self.settings.os) == "OHOS":
            toolchain.cache_variables["CMAKE_SYSTEM_NAME"] = "OHOS"
            toolchain.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8"
                else str(self.settings.arch)
            )
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

    def test(self):
        if not can_run(self):
            raise ConanException(
                "libspctag tests must execute on the native OHOS target"
            )

        bindir = self.cpp.build.bindirs[0]
        self.run(os.path.join(bindir, "test_libspctag"), env="conanrun")
        discovered = 1
        assertions = 48
        if str(self.settings.os) == "OHOS":
            self.run(
                os.path.join(bindir, "test_libspctag_ohos"), env="conanrun"
            )
            discovered += 1
            assertions += 8

        test_result = {
            "executed": True,
            "passed": True,
            "command": "libspctag consumer binaries (%d assertions)" % assertions,
            "discovered": discovered,
            "passedCount": discovered,
        }
        line = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_result)
        print(line, flush=True)
        self.output.info(line)

        dependency = self.dependencies[self.tested_reference_str]
        upstream_path = os.path.join(
            dependency.package_folder, "res", "upstream_test_result.json"
        )
        if not os.path.isfile(upstream_path):
            raise ConanException(
                "upstream_test_result.json is missing; upstream test did not run"
            )
        with open(upstream_path, "r", encoding="utf-8") as handle:
            upstream = json.load(handle)
        if (
            upstream.get("status") != "passed"
            or upstream.get("discovered") != 1
            or upstream.get("executed") != 1
            or upstream.get("passed") != 1
            or upstream.get("failed") != 0
        ):
            raise ConanException("invalid upstream test evidence: %r" % upstream)
        upstream_line = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream)
        print(upstream_line, flush=True)
        self.output.info(upstream_line)
