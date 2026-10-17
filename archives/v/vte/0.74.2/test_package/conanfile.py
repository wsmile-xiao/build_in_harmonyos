#!/usr/bin/env python3
"""Conan test_package — vte 0.74.2

Substantive smoke test (R34): calls vte_terminal_new() and vte's pty API
to verify the library links and core symbols are present.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class VteTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # PkgConfigDeps lets test.c pick up vte's full transitive include
    # + link flags via pkg-config (CMakeDeps drops harfbuzz's include dir).
    generators = "CMakeToolchain", "PkgConfigDeps"

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
        # Also run the binary directly to verify it executes
        self.run(f"{os.path.join(self.cpp.build.bindirs[0], 'test_vte')}", env="conanrun")
