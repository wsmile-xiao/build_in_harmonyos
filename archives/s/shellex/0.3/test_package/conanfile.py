"""Conan test_package — consumer behaviour test for the packaged shellex.

Loads the real shellex_preload.so into a live /bin/sh process via
LD_PRELOAD and asserts the shell still executes commands and the library
actually loads; additionally syntax-checks the generated launcher script.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class ShellexTestConan(ConanFile):
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
        runner = os.path.join(self.cpp.build.bindirs[0], "test_shellex")
        dep = self.dependencies["shellex"]
        preload_so = os.path.join(
            dep.package_folder, "lib", "shellex", "shellex_preload.so"
        )
        launcher = os.path.join(dep.package_folder, "bin", "shellex")
        self.run(f"{runner} {preload_so} {launcher}")
