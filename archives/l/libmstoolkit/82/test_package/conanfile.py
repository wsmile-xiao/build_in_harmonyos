#!/usr/bin/env python3
"""Real consumer tests for libmstoolkit/82."""

import json
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LibmstoolkitTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        toolchain = CMakeToolchain(self)
        if str(self.settings.os) == "OHOS":
            # Device CMake lacks a HarmonyOS platform module. The profile
            # compiler still supplies the real OHOS target toolchain.
            toolchain.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            toolchain.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(
                self.settings.arch
            )
            toolchain.cache_variables["LIBMSTOOLKIT_BUILD_OHOS_TEST"] = True
        else:
            toolchain.cache_variables["LIBMSTOOLKIT_BUILD_OHOS_TEST"] = False
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            raise ConanInvalidConfiguration(
                "libmstoolkit test_package must execute on the target"
            )

        tmpdir = os.path.join(self.build_folder, "runtime-tmp")
        os.makedirs(tmpdir, exist_ok=True)
        old_tmp = os.environ.get("TMPDIR")
        os.environ["TMPDIR"] = tmpdir
        passed = 0
        discovered = 2 if str(self.settings.os) == "OHOS" else 1
        try:
            generic = os.path.join(self.cpp.build.bindir, "test_libmstoolkit")
            self.run('"{}"'.format(generic), env="conanrun")
            passed += 1
            if str(self.settings.os) == "OHOS":
                specific = os.path.join(
                    self.cpp.build.bindir, "test_ohos_libmstoolkit"
                )
                self.run('"{}"'.format(specific), env="conanrun")
                passed += 1
        finally:
            if old_tmp is None:
                os.environ.pop("TMPDIR", None)
            else:
                os.environ["TMPDIR"] = old_tmp

        test_result = {
            "executed": True,
            "passed": passed == discovered,
            "command": "test_libmstoolkit"
            + (" + test_ohos_libmstoolkit" if discovered == 2 else ""),
            "discovered": discovered,
            "passedCount": passed,
        }
        marker = json.dumps(test_result, ensure_ascii=False)
        print("HMBS_TEST_PACKAGE_RESULT=" + marker, flush=True)
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + marker)

        result_path = os.path.join(
            self.dependencies["libmstoolkit"].package_folder,
            "res",
            "upstream_test_result.json",
        )
        if not os.path.isfile(result_path):
            raise ConanInvalidConfiguration(
                "missing upstream test census evidence in package"
            )
        with open(result_path, encoding="utf-8") as result_file:
            upstream = json.load(result_file)
        required = {
            "status": "no_tests",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
        }
        if any(upstream.get(key) != value for key, value in required.items()):
            raise ConanInvalidConfiguration(
                "invalid upstream test census evidence: {}".format(upstream)
            )
        upstream_marker = json.dumps(upstream, ensure_ascii=False)
        print("HMBS_UPSTREAM_TEST_RESULT=" + upstream_marker, flush=True)
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + upstream_marker)
