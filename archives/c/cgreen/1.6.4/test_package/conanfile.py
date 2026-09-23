#!/usr/bin/env python3
"""Conan test_package for cgreen — consumers written with cgreen itself.

Runs four executables that link the packaged libcgreen and exercise its public
API end-to-end (closed loop: a test framework proving itself through a real
consumer):
  test_cgreen_c        — C API assertions, string/pointer/double constraints,
                         INT_MIN/MAX boundary + empty/long-string cases
  test_cgreen_boundary — dedicated boundary & edge-condition suite
  test_cgreen_failpath — error path: an intentionally failing suite must be
                         reported through run_test_suite()'s non-zero return
  test_cgreen_cpp      — C++ consumer (libcgreen C++ linkage): STL string
                         constraints + user-defined type equality
All executables return 0 only when the observed behaviour matches the
expectations above; any run_test_suite() failure propagates a non-zero exit.
"""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class CgreenTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()

        tc = CMakeToolchain(self)
        if str(self.settings.os) == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

        runenv = VirtualRunEnv(self)
        runenv.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return
        bindir = self.cpp.build.bindirs[0]
        for exe in ("test_cgreen_c", "test_cgreen_boundary", "test_cgreen_failpath", "test_cgreen_cpp"):
            self.run(os.path.join(bindir, exe), env="conanrun")
