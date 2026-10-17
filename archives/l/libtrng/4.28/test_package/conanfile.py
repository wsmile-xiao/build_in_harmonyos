import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibtrngTestConan(ConanFile):
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
        # Run the self-checking Catch2 binary directly (R34: substantive API test).
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_libtrng"), env="conanrun")
