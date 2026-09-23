#!/usr/bin/env python3
"""Conan test_package for mujs — real API smoke test (R34).

Calls the public MuJS API (mujs.h) to compile & run a JS snippet,
verifies the returned value — not a print-only shell test.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class MujsTestConan(ConanFile):
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
        # Also verify the installed CLI tool works end-to-end (R38/L0k).
        # mujs has no --version flag; run a real JS snippet with the
        # absolute path from the tested package (avoids PATH injection).
        mujs_exe = os.path.join(
            self.dependencies[self.tested_reference_str].package_folder,
            "bin", "mujs")
        smoke = os.path.join(self.source_folder, "cli_smoke.js")
        self.run(f'"{mujs_exe}" "{smoke}"', env="conanrun")
