#!/usr/bin/env python3
"""Conan test_package for dewalls 1.0.0 — links libdewalls and exercises the
public parser API (WallsSurveyParser) instead of a print-only stub."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class DewallsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # dewalls keeps qt/5.15.19 as a private (visible=False) build require;
        # the consumer resolves Qt5 itself via CMAKE_PREFIX_PATH + find_package(Qt5).
        self.requires("qt/5.15.19")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # qt/5.15.19 ships its own Qt5Config.cmake with cmake_find_mode=none:
        # CMakeDeps must NOT generate a qt target nor a find_dependency(qt) in
        # dewalls-config.cmake. Consumers resolve Qt5 themselves via
        # CMAKE_PREFIX_PATH.
        deps = CMakeDeps(self)
        qt = self.dependencies.get("qt", None)
        if qt is not None:
            deps.set_property("qt", "cmake_find_mode", "none")
        deps.generate()

        tc = CMakeToolchain(self)
        if qt is not None:
            tc.cache_variables["CMAKE_PREFIX_PATH"] = qt.package_folder
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Build dir layout (cmake_layout): bindirs[0] holds test_dewalls.
        bindirs = self.cpp.build.bindirs
        if not bindirs:
            raise RuntimeError("test_dewalls executable directory was not produced")
        executable = os.path.join(bindirs[0], "test_dewalls")
        if not os.path.isfile(executable):
            raise RuntimeError("test_dewalls executable not found: " + executable)
        self.run(executable, env="conanrun")