import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Lib3dsTestConan(ConanFile):
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
        # R34: run the binary directly as well, so the in-memory API
        # checks (and the "CHECK passed: N" tally) reach stdout verbatim.
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_lib3ds"), env="conanrun")
