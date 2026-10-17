import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class SislTestConan(ConanFile):
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
        executable = os.path.join(self.build_folder, "test_sisl")
        self.run(executable, env="conanrun")
