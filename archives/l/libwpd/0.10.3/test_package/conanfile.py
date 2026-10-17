#!/usr/bin/env python3
"""Consumer test for libwpd/0.10.3.

Builds the C++ consumer test against the installed package and runs it, then
exercises the packaged conversion tools through the shell test.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibwpdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # libwpd's headers expose librevenge types, so the consumer needs it
        # on the include path and link line as well.
        self.requires("librevenge/0.0.5")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        # Run it once more directly so the individual assertion results end
        # up in the build log as evidence rather than only on failure.
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_libwpd"),
                 env="conanrun")
        # The package also ships conversion tools; drive one end to end.
        tool = os.path.join(self.dependencies["libwpd"].package_folder,
                            "bin", "wpd2text")
        script = os.path.join(os.path.dirname(__file__),
                              "test_libwpd_cli.sh")
        self.run(f'sh "{script}" "{tool}"', env="conanrun")
