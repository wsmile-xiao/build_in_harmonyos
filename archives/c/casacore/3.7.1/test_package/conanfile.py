from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
import os


class TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Run the test binary directly - tests casacore Vector/Array API
        test_bin = os.path.join(self.build_folder, "test_casacore")
        self.run(test_bin, env="conanrun")
