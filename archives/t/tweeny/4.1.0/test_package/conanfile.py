#!/usr/bin/env python3
"""Consumer test — tweeny/4.1.0 (Conan L1 test).

Builds a real C++ program against the installed headers (resolved through the
upstream CMake package config exported by the recipe) and asserts on tweening
behaviour: linear interpolation, multi-value tweens, easing shape, seek/step
semantics, callbacks and end-of-range clamping.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class TweenyTestConan(ConanFile):
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
        cmake = CMake(self)
        cmake.test()
        # Explicit re-execution of the consumer binary: CI L0d requires a
        # self.run() in test(), and it also guards against a silently lost
        # ctest registration. The binary prints its assertion summary and
        # exits non-zero on failure.
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_tweeny"),
                 env="conanrun")
