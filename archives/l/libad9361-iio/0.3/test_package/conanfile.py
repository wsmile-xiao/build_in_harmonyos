from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
import os


class Libad9361iioTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
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
        # Consumer test: compile + link against the installed package and
        # exercise the device-independent clock-chain algorithm.
        cmd = os.path.join(self.cpp.build.bindir, "test_libad9361")
        self.run(cmd, env="conanrun")
