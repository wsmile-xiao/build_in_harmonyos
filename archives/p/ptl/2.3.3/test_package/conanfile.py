#!/usr/bin/env python3
"""Conan consumer test for PTL 2.3.3."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class PtlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        executable = os.path.join(self.cpp.build.bindir, "test_ptl")
        runtime_environment = Environment()
        for dependency in self.dependencies.values():
            package_folder = getattr(dependency, "package_folder", None)
            if not package_folder:
                continue
            for libdir in dependency.cpp_info.aggregated_components().libdirs:
                runtime_libdir = (
                    libdir
                    if os.path.isabs(libdir)
                    else os.path.join(package_folder, libdir)
                )
                runtime_environment.prepend_path("LD_LIBRARY_PATH", runtime_libdir)
        with runtime_environment.vars(self).apply():
            self.run(executable, env="conanrun")
