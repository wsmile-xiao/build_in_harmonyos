from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
import os


class LibpillowfightTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"
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
        # Verify the binary was built successfully
        bin_path = os.path.join(self.cpp.build.bindir, "test_consumer")
        self.run(f"file {bin_path}")
