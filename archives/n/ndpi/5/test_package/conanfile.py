#!/usr/bin/env python3
"""Conan test_package for ndpi 5 — consumer check against the real API.

Builds test.c (detection-module lifecycle + protocol database queries)
with CMake and runs it via ctest. Emits HMBS_TEST_PACKAGE_RESULT with the
real assertion count (7 checks in test.c).
"""

import json
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout


class NdpiTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # 7 explicit checks in test.c (init/finalize/num/HTTP/DNS/flow/rev).
        command = "ctest --output-on-failure -R test_ndpi"
        marker = {
            "executed": True,
            "passed": True,
            "command": command,
            "discovered": 7,
            "passedCount": 7,
        }
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries directly,
        # so wrap the test command with bash from the build environment.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        try:
            self.run('%s -c "%s"' % (bash, command), env="conanrun")
        except Exception:
            marker["passed"] = False
            marker["passedCount"] = 0
            self.output.info(
                "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
            )
            print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))
            raise
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
        )
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))

        # Re-emit upstream `make check` evidence persisted by package() to
        # res/upstream_test_result.json. build() is skipped on Conan cache
        # hits, so without this every cached round reports incomplete (same
        # root cause as ali 0.8.0). No synthesis: missing/invalid evidence
        # fails instead of fabricating a pass.
        try:
            dep = self.dependencies["ndpi"]
        except Exception:
            dep = self.dependencies[self.tested_reference_str]
        candidates = (
            os.path.join(dep.package_folder, "res", "upstream_test_result.json"),
            os.path.join(dep.package_folder, "upstream_test_result.json"),
        )
        for path in candidates:
            if not os.path.isfile(path):
                continue
            with open(path, "r", encoding="utf-8") as f:
                result = json.load(f)
            self.output.info(
                "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False)
            )
            print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False))
            ok_shape = (
                isinstance(result, dict)
                and result.get("status") == "passed"
                and int(result.get("discovered", 0)) > 0
                and int(result.get("executed", 0)) == int(result.get("discovered", 0))
                and int(result.get("passed", 0)) == int(result.get("discovered", 0))
                and int(result.get("failed", 0)) == 0
                and int(result.get("skipped", 0)) == 0
            )
            if not ok_shape:
                raise ConanException("upstream test evidence invalid: %s" % (result,))
            return
        raise ConanException("upstream_test_result.json not found in package")
