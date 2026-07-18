#!/usr/bin/env python3
"""Conan test package for aws-c-compression 0.3.2."""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.files import save


class AwsCCompressionConanTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def generate(self):
        include_dirs = []
        for dependency in self.dependencies.values():
            package_folder = dependency.package_folder
            if package_folder:
                include_dir = os.path.join(package_folder, "include")
                if os.path.isdir(include_dir):
                    include_dirs.append(include_dir.replace("\\", "/"))
        content = "set(AWS_TEST_INCLUDE_DIRS\n"
        for include_dir in sorted(set(include_dirs)):
            content += f'    "{include_dir}"\n'
        content += ")\n"
        save(self, os.path.join(self.generators_folder, "aws_test_includes.cmake"), content)

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("aws-c-common/0.12.6")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            test_bin = os.path.join(self.cpp.build.bindirs[0], "test_aws_c_compression")
            self.run(test_bin, env="conanrun")
