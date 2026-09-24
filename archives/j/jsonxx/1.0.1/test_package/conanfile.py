#!/usr/bin/env python3
"""Conan test_package — jsonxx 1.0.1 L1 official test.

CI runs this automatically via `conan create` (which invokes test_package).
"""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class JsonxxTestConan(ConanFile):
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
        # Alternatively, run the binary directly:
        # self.run(f"{os.path.join(self.cpp.build.bindirs[0], 'test_jsonxx')}", env="conanrun")
