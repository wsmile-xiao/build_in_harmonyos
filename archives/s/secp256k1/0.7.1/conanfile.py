#!/usr/bin/env python3
"""Conan recipe — CMake project (secp256k1 0.7.1).

Optimized C library for EC operations on curve secp256k1.
Build system: CMake
License: MIT

This template enforces R26: BUILD_SHARED_LIBS=OFF for terminal tools.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Secp256k1Conan(ConanFile):
    name = "secp256k1"
    version = "0.7.1"
    description = "Optimized C library for EC operations on curve secp256k1"
    license = "MIT"
    homepage = "https://github.com/bitcoin-core/secp256k1"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.variables["SECP256K1_ENABLE_MODULE_ECDH"] = True
        tc.variables["SECP256K1_ENABLE_MODULE_SCHNORRSIG"] = True
        tc.variables["SECP256K1_ENABLE_MODULE_EXTRAKEYS"] = True
        tc.variables["SECP256K1_BUILD_BENCHMARK"] = False
        tc.variables["SECP256K1_BUILD_TESTS"] = False
        tc.variables["SECP256K1_BUILD_EXHAUSTIVE_TESTS"] = False
        tc.variables["SECP256K1_BUILD_CTIME_TESTS"] = False
        tc.variables["SECP256K1_BUILD_EXAMPLES"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build(cli_args=["--parallel", "1"])

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["secp256k1"]
