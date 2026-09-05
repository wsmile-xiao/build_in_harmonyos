#!/usr/bin/env python3
"""Conan test_package for cctools 7.15.9.

R34: This test must actually depend on the tested package.
cctools produces both libraries (libdttools, libchirp, etc.) and
executables (makeflow, chirp_server, work_queue_worker, etc.).

This test:
1. Compiles a small C program that links against libdttools and calls
   the debug() API (substantive dependency, R34).
2. Runs the compiled program to verify linking succeeds.
3. Runs the makeflow binary to verify executables are installed.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CctoolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # R34: run the compiled test binary (links libdttools, calls debug())
        self.run(os.path.join(self.build_folder, "test_cctools"), env="conanrun")
        # E298: invoke the packaged CLI by its absolute path inside the tested
        # package folder. conanrun (VirtualRunEnv) does not put dependency
        # bindirs on PATH; a bare "makeflow" would only resolve via the
        # ambient shell PATH — passing on dev machines that have a stale
        # system install, failing on clean CI with Error 127 (CI #36792).
        makeflow = os.path.join(
            self.dependencies["cctools"].package_folder, "usr", "bin", "makeflow"
        )
        self.run(f'"{makeflow}" --version', env="conanrun")
