import os
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import cross_building


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
        if not cross_building(self):
            # This CI's Conan self.run() API uses ignore_errors=False to fail
            # the build on a non-zero exit code; it does not accept check=True.
            self.run(os.path.join(self.cpp.build.bindirs[0], "test_ncurses"), env="conanrun", ignore_errors=False)
