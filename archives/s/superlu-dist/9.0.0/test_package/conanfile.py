#!/usr/bin/env python3
"""Conan test_package for superlu-dist 9.0.0 — real pdgssvx_ABglobal solve (R34).

Consumes the packaged library from a separate project and verifies that the
solver reproduces a known exact solution to 1e-8, then that the residual
||Ax-b|| is also below 1e-8.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class SuperluDistTestConan(ConanFile):
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
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_superlu_dist")
        # A single rank is enough: superlu_gridinit(MPI_COMM_WORLD, 1, 1, ...)
        # forms a valid 1x1 grid and OpenMPI's singleton init covers the
        # no-mpiexec case, so the assertion run does not depend on the
        # launcher being present (env="conanrun" supplies MPI's runtime vars).
        self.run(f'"{bin_path}"', env="conanrun")
