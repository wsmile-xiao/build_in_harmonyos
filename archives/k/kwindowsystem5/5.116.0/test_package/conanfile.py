#!/usr/bin/env python3
"""Conan test_package for kwindowsystem5 5.116.0.

L1 consumer test: compiles a small program that calls real KF5WindowSystem
APIs (KWindowSystem::self / numberOfDesktops / KWindowInfo) and links against
the delivered libKF5WindowSystem package.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Kwindowsystem5TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # The consumer also needs the full Qt5 (Qt5::Widgets) at link time.
        self.requires("qt/5.15.19")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # The consumer links shared libKF5WindowSystem and Qt5 modules; use an
        # explicit run under the run environment so LD_LIBRARY_PATH / PATH
        # point at the package folders at runtime.
        self.run(
            f'"{os.path.join(self.cpp.build.bindir, "test_kwindowsystem5")}"',
            env="conanrun",
        )
