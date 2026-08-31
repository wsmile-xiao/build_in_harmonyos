from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
import os


class BoostSmlTestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_CXX_STANDARD"] = "14"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Run the compiled consumer binary: it builds a real Boost.SML state
        # machine and asserts transitions (not a stub).
        test_bin = os.path.join(self.cpp.build.bindir, "test_package")
        self.run(test_bin, env="conanrun")