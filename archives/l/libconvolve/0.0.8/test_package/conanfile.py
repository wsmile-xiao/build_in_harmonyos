"""Verify the installed libconvolve package through its public API."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibconvolveTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        self.run('cmake --build "{}" --parallel 1'.format(self.build_folder))

    def test(self):
        self.run(os.path.join(self.build_folder, "test_libconvolve"), env="conanrun")
