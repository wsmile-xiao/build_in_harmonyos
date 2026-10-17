import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self.run(
            "ctest --test-dir . --output-on-failure",
            cwd=self.build_folder,
        )
