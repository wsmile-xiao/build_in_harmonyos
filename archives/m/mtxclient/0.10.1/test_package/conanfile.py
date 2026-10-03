#!/usr/bin/env python3
"""test_package: real consumer of the installed mtxclient public API."""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class MtxclientTestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # mtxclient's public headers include <nlohmann/json_fwd.hpp> (every
        # mtx/events, mtx/requests, mtx/responses type), but the recipe's
        # cpp_info.requires chain to nlohmann_json does not reach this consumer:
        # nlohmann_json is header-only, so Conan creates no package node for it
        # and package_info() cannot re-declare its include dir on the
        # MatrixClient target. The matrix_client shared object does keep its
        # DT_NEEDED edges, so only the headers are missing. Declaring the same
        # version the recipe pins supplies them -- the same explicit-declaration
        # doctrine the coeurl recipe documents for fmt (E216 family).
        self.requires("nlohmann_json/3.12.0")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            test_bin = os.path.join(self.cpp.build.bindirs[0], "test_package")
            self.run(test_bin, env="conanrun")
