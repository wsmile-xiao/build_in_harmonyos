from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import can_run
import os


class TestConan(ConanFile):
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
        if can_run(self):
            # Run consumer test
            self.run(os.path.join(self.cpp.build.bindirs[0], "test_package"), env="conanrun")
            # Run upstream tests (no hardware required)
            self.run(os.path.join(self.cpp.build.bindirs[0], "test_core"), env="conanrun")
            self.run(os.path.join(self.cpp.build.bindirs[0], "test_put"), env="conanrun")
