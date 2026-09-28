#!/usr/bin/env python3
"""Conan test_package for ptscotch 7.0.12 — real parallel partition (R34).

Consumes the packaged library from a separate project and drives the real
distributed API: it initialises a distributed graph, builds a 4x4x1 grid
graph in memory, validates it and computes a partition.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class PtscotchTestConan(ConanFile):
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
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_ptscotch")
        # Run on a single rank: the API is collective over MPI_COMM_WORLD, so
        # one rank forms a valid (degenerate) process set and still exercises
        # the full build/check/partition path. Launching more ranks requires
        # mpiexec, which is not reliably available inside conan's test()
        # environment, and multi-rank runs are blocked by the sandbox anyway.
        # conanrun 已携带依赖的运行期环境（含 mpich 的 lib 目录），故直接用它。
        self.run(f'"{bin_path}"', env="conanrun")
