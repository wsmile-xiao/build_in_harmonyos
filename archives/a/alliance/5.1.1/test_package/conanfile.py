import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class AllianceTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
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
        binary = os.path.join(self.cpp.build.bindirs[0], "test_alliance")
        if not os.path.isfile(binary):
            raise RuntimeError(f"Expected test executable is missing: {binary}")
        if can_run(self):
            self.run(f'"{binary}"', env="conanrun")
        else:
            self.output.info("Cross-built consumer; runtime is validated on the OHOS emulator.")
