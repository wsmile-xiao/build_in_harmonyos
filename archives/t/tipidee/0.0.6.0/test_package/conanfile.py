from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain
import os


class TipideeTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # tipidee headers include skalibs headers, so the test needs it directly
        self.requires("skalibs/2.15.1.0")

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        self.run("./tipidee_test", env="conanrun")
