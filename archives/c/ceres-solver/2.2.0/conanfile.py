#!/usr/bin/env python3
"""Conan recipe for ceres-solver 2.2.0 — CMake projects.

Ceres Solver is a large scale non-linear optimization library.
This recipe uses MINIGLOG=ON (internal glog implementation) since glog
is not available in the OHOS Conan repository.

This template enforces R26: BUILD_SHARED_LIBS=OFF for static library.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, rm
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class CeresSolverConan(ConanFile):
    name = "ceres-solver"
    version = "2.2.0"
    description = "A large scale non-linear optimization library"
    license = "BSD-3-Clause"
    homepage = "https://ceres-solver.org/"
    url = ""  # CI fills this

    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "miniglog": [True, False],
    }
    default_options = {
        "shared": False,
        "miniglog": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("eigen/3.4.0")

    def layout(self):
        # Use custom build folder to avoid conflict with Bazel BUILD file
        cmake_layout(self, build_folder="cmake-build")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Remove Bazel BUILD file to avoid potential conflict with CMake build dir
        rm(self, "BUILD", self.source_folder)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        # R26: Static library by default
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Use internal miniglog instead of external glog (not available in OHOS repo)
        tc.variables["MINIGLOG"] = "ON" if self.options.miniglog else "OFF"
        tc.variables["GFLAGS"] = "OFF"
        tc.variables["BUILD_EXAMPLES"] = "OFF"
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j6"])

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["ceres"]
        # Propagate eigen headers to consumers (ceres headers include Eigen)
        self.cpp_info.requires = ["eigen::eigen"]
        # When MINIGLOG=ON, add miniglog include path so "glog/logging.h" resolves
        if self.options.miniglog:
            self.cpp_info.includedirs.append(
                os.path.join("include", "ceres", "internal", "miniglog")
            )
