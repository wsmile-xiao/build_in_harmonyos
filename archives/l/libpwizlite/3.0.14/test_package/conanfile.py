#!/usr/bin/env python3
"""Consumer test for libpwizlite 3.0.14.

Upstream ships NO test directory and registers no tests (only CPack source
ignore entries mention tests/) — N=0 declared in the PR statistics table.
This consumer test backs the declaration with real API usage: it parses an
inline minimal mzML document through MSDataFile/MSData and asserts run,
instrument and spectrum metadata, then exercises the SpectrumList access
path (the core of what pappsomspp consumes libpwizlite for).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, cmake_layout
from conan.tools.env import Environment


class LibpwizliteTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("boost/1.84.0")
        self.requires("zlib/1.3.1")

    def generate(self):
        deps = CMakeDeps(self)
        deps.set_property("zlib", "cmake_file_name", "ZLIB")
        deps.set_property("zlib", "cmake_target_name", "ZLIB::ZLIB")
        deps.generate()

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH",
                                 os.path.join(dep.package_folder, "lib"))
        env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        with env.vars(self).apply():
            cmd = os.path.join(self.cpp.build.bindirs[0], "test_pwizlite")
            self.run(f"{cmd}", env="conanrun")
