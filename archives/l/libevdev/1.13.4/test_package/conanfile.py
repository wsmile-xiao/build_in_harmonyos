#!/usr/bin/env python3
"""Conan test_package — libevdev 1.13.4 L1 test (Conan L1 official test).

CI runs this automatically via `conan create` (which invokes test_package).

test() explicitly runs the built test binary with VirtualRunEnv (L1 gate:
the test must be actually compiled AND executed — cmake.test() alone does
not satisfy the platform gate).

File location: archives/l/libevdev/1.13.4/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LibevdevTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return
        suffix = ".exe" if str(self.settings.os) == "Windows" else ""
        executable = os.path.join(self.cpp.build.bindirs[0], "test_libevdev" + suffix)
        self.run(f'"{executable}"', env="conanrun", cwd=self.build_folder)
