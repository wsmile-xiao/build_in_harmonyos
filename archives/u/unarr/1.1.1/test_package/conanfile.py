import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class UnarrTestConan(ConanFile):
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
        # Real consumer: opens an in-memory tar archive through the public API and
        # asserts the entry metadata and decompressed payload.
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_unarr"), env="conanrun")
