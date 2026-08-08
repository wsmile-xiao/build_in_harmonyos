import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class SfmlTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(cli_args=["--parallel", "1"])

    def test(self):
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_sfml"), env="conanrun")
