import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class ZxcvbnCTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        # OHOS make cannot create the jobserver FIFO used by parallel builds.
        cmake.build(build_tool_args=["-j1"])

    def test(self):
        if can_run(self):
            self.run(os.path.join(self.cpp.build.bindirs[0], "zxcvbn_test"),
                     env="conanrun")
