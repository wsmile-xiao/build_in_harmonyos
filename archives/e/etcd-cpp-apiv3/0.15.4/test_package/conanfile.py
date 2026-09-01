#!/usr/bin/env python3
"""Conan consumer tests for etcd-cpp-apiv3 0.15.4 (core-only runtime)."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class EtcdCppApiv3TestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()

        # grpc and protobuf ship cmake_find_mode=none, so CMakeDeps does not
        # generate configs for them. The generated etcd-cpp-apiv3-config.cmake
        # find_dependency()s them (CONFIG mode), so point each find_package
        # at the installed config files inside the registry packages
        # (mirrors the grpc recipe/test wiring).
        grpc = self.dependencies["grpc"]
        protobuf = self.dependencies["protobuf"]
        abseil = self.dependencies["abseil-cpp"]

        tc = CMakeToolchain(self)
        tc.variables["gRPC_DIR"] = os.path.join(
            grpc.package_folder, "lib", "cmake", "grpc"
        ).replace("\\", "/")
        tc.variables["Protobuf_DIR"] = os.path.join(
            protobuf.package_folder, "lib", "cmake", "protobuf"
        ).replace("\\", "/")
        tc.variables["utf8_range_DIR"] = os.path.join(
            protobuf.package_folder, "lib", "cmake", "utf8_range"
        ).replace("\\", "/")
        tc.variables["absl_DIR"] = os.path.join(
            abseil.package_folder, "lib", "cmake", "absl"
        ).replace("\\", "/")
        # gRPCConfig.cmake locates OpenSSL through the built-in FindOpenSSL
        # module, which needs the registry package root.
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
