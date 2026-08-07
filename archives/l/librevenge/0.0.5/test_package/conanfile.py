#!/usr/bin/env python3
"""Test package for librevenge — verifies RVNGStringVector and RVNGPropertyList APIs."""
import os
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def test(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # boost/1.90.0.3 ships shared libs; ctest's test_package binary links
        # libboost_*.so at runtime, so expose every dep's lib dir to the
        # dynamic loader (Conan 2 self.run env is a list of "KEY=VALUE").
        lib_paths = []
        for name, dep in self.dependencies.items():
            dep_lib = os.path.join(str(dep.package_folder), "lib")
            if os.path.isdir(dep_lib):
                lib_paths.append(dep_lib)
        lib_paths.append(os.environ.get("LD_LIBRARY_PATH", ""))
        os.environ["LD_LIBRARY_PATH"] = ":".join(lib_paths)
        # L0d: test() must include self.run() call
        self.run("ctest --output-on-failure")
