import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class AriaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

    def test(self):
        test_binary = os.path.join(self.build_folder, "test_aria")
        self.run(f'"{test_binary}"', env="conanrun")
