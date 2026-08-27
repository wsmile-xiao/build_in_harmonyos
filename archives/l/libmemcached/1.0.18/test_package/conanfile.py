from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.files import copy
import os

class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"
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
