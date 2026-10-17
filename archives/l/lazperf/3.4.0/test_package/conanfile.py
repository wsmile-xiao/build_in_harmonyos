import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LazperfTestConan(ConanFile):
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
        cmake = CMake(self)
        cmake.test()
        # R34: also run the binary directly so the substantive API assertions
        # in test_lazperf.cpp are executed even if ctest registration changes.
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_lazperf"),
                 env="conanrun")
