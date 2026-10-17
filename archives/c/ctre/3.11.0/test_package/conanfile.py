#!/usr/bin/env python3
"""Conan test_package — ctre 3.11.0.

Consumer test: build and run test_package.cpp against the packaged
ctre::ctre INTERFACE target (C++17). The binary exercises real CTRE APIs
(match/search/numeric/named captures) and prints HMBS_TEST_PACKAGE_RESULT
itself; test() additionally re-emits the packaged HMBS_UPSTREAM_TEST_RESULT
so cache-hit ("Already installed!") rounds still carry upstream evidence.
"""

import json
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_CXX_STANDARD"] = "17"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not cross_building(self):
            cmake = CMake(self)
            cmake.test()
            # L0d: test() must hold a self.run() execution of the tested package.
            self.run(os.path.join(self.cpp.build.bindirs[0], "test_package"), env="conanrun")
            self._reemit_upstream_marker()

    def _reemit_upstream_marker(self):
        candidates = []
        try:
            candidates.append(os.path.join(self.dependencies["ctre"].package_folder, "res", "hmbs_upstream.json"))
        except Exception:
            pass
        for path in candidates:
            if path and os.path.isfile(path):
                try:
                    with open(path, encoding="utf-8") as handle:
                        data = json.load(handle)
                    self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(data, ensure_ascii=False))
                    return
                except OSError:
                    pass
