#!/usr/bin/env python3
"""Conan test_package — installed-package API tests for libopencad 0.2.0.

L1 consumer test: builds a small program that really opens a DWG sample
file through the public C API (opencad_api.h) and verifies the parsed
layers/geometry, so it is more than a header-only include check.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LibopencadTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    # NOTE: no binary test data is stored in the git repo (PR diffs cannot
    # carry binary patch data). The DWG sample is shipped by the libopencad
    # package itself under res/ and located via the dependency graph.

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            raise ConanException("libopencad target consumers are not runnable")
        # The DWG sample is read from the dependency package's res/ dir
        # (shipped by the recipe from the upstream source tarball), so run
        # from that directory; the executable must be an absolute path
        # since we cd away from the build dir.
        executable = os.path.abspath(
            os.path.join(self.cpp.build.bindir, "test_libopencad"))
        res_dir = os.path.join(
            self.dependencies["libopencad"].package_folder, "res")
        self.run(f'cd "{res_dir}" && "{executable}"', env="conanrun")
