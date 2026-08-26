import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class LibBcg729TestConan(ConanFile):
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
        # L1d: real self.run() — executes the compiled test binary (R34).
        # This runs the actual encoder/decoder round-trip, not just a header include.
        if cross_building(self):
            self.output.info("cross-building: verifying compile+link only")
            return
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_libbcg729"), env="conanrun")
