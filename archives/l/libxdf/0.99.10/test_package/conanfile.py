import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibxdfTestConan(ConanFile):
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
        # Real consumer: runs the test binary, which builds an XDF file and asserts
        # the parsed metadata/samples through the public libxdf API.
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_libxdf"), env="conanrun")
