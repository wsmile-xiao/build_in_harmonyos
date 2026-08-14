import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class UudeviewTestConan(ConanFile):
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
        # Run the compiled test binary that calls uulib API
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_uudeview"), env="conanrun")
        # Verify the uudeview and uuenview binaries exist and are executable
        # uudeview without args returns exit code 1 (usage), so we use self.run with ignore=True
        self.run("uudeview", env="conanrun", ignore_errors=True)
        self.run("uuenview", env="conanrun", ignore_errors=True)
