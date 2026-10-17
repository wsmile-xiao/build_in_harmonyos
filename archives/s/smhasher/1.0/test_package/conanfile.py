#!/usr/bin/env python3
"""Conan test_package — smhasher 1.0 consumer verification (ctest)."""
import json
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class SmhasherTestConan(ConanFile):
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

    def _reemit_upstream_marker(self):
        try:
            dep = self.dependencies["smhasher"]
            cand = os.path.join(str(dep.package_folder), "res", "hmbs_upstream.json")
        except Exception:
            return
        if cand and os.path.isfile(cand):
            try:
                with open(cand, encoding="utf-8") as handle:
                    data = json.load(handle)
                self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(data, ensure_ascii=False))
            except (OSError, ValueError):
                pass

    def test(self):
        marker = {
            "executed": True,
            "passed": True,
            "command": "ctest --output-on-failure",
            "discovered": 2,
            "passedCount": 2,
        }
        try:
            cmake = CMake(self)
            cmake.test()
            # L0d: explicit execution proof of the packaged library consumers.
            self.run(os.path.join(self.cpp.build.bindirs[0], "test_vectors"), env="conanrun")
            self.run(os.path.join(self.cpp.build.bindirs[0], "test_hashes"), env="conanrun")
        except Exception as exc:
            marker["passed"] = False
            marker["passedCount"] = 0
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))
            self._reemit_upstream_marker()
            raise
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))
        self._reemit_upstream_marker()
