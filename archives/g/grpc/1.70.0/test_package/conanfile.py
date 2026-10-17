#!/usr/bin/env python3
"""Conan consumer tests for grpc 1.70.0 (CMake)."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class GrpcTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()

        grpc_pkg = self.dependencies["grpc"]
        tc = CMakeToolchain(self)
        # grpc installs its CMake config under lib/cmake/grpc; point
        # find_package(gRPC CONFIG) at it directly.
        tc.variables["gRPC_DIR"] = os.path.join(
            grpc_pkg.package_folder, "lib", "cmake", "grpc"
        ).replace("\\", "/")
        # gRPCConfig.cmake find_dependency()s Protobuf/absl/c-ares/re2;
        # protobuf ships cmake_find_mode=none so its config must be located
        # explicitly (mirrors the main recipe's wiring).
        protobuf = self.dependencies["protobuf"]
        tc.variables["Protobuf_DIR"] = os.path.join(
            protobuf.package_folder, "lib", "cmake", "protobuf"
        ).replace("\\", "/")
        tc.variables["utf8_range_DIR"] = os.path.join(
            protobuf.package_folder, "lib", "cmake", "utf8_range"
        ).replace("\\", "/")
        abseil = self.dependencies["abseil-cpp"]
        tc.variables["absl_DIR"] = os.path.join(
            abseil.package_folder, "lib", "cmake", "absl"
        ).replace("\\", "/")
        openssl = self.dependencies["openssl"]
        tc.variables["OPENSSL_ROOT_DIR"] = openssl.package_folder.replace("\\", "/")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            self.run(
                "ctest --output-on-failure --no-tests=error",
                cwd=self.build_folder,
                env="conanrun",
            )
