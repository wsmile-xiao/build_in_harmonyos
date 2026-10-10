"""Consumer test for the installed vnlog C API."""

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class VnlogTestConan(ConanFile):
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
        # Run the registered consumer test explicitly for CI gate L0d.
        self.run("ctest --output-on-failure", cwd=self.build_folder)
