#!/usr/bin/env python3
import os
from conan import ConanFile
from conan.tools.cmake import CMake


class ConvlitTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        cmake = CMake(self)
        clit = os.path.join(self.dependencies["convlit"].package_folder, "bin", "clit")
        cmake.configure(variables={"CLIT_PATH": clit})
        cmake.build()

    def test(self):
        test_bin = os.path.join(self.build_folder, "test_convlit")
        clit = os.path.join(self.dependencies["convlit"].package_folder,
                            "bin", "clit")
        self.run(f'"{test_bin}" "{clit}"', env="conanrun")
