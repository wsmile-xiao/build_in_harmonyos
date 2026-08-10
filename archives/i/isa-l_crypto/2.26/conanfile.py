#!/usr/bin/env python3
"""Conan recipe for isa-l_crypto 2.26.

Intel Storage Acceleration Library - Crypto implementation.
Provides hardware-accelerated cryptographic functions for MD5, SHA1, SHA256,
SHA512, SM3, multi-hash SHA, AES-GCM/CBC/XTS, and rolling hash.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class IsaLCryptoConan(ConanFile):
    name = "isa-l_crypto"
    version = "2.26"
    description = "Intel Storage Acceleration Library - Crypto implementation"
    license = "BSD-3-Clause"
    homepage = "https://github.com/intel/isa-l_crypto"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

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
        # CMake doesn't recognize HarmonyOS as a system name; use Linux
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_TESTS"] = "OFF"
        tc.variables["BUILD_PERF"] = "OFF"
        tc.variables["SAFE_DATA"] = "ON"
        tc.variables["SAFE_PARAM"] = "ON"
        # Use external GNU assembler for SVE/SVE2 assembly (.req register aliases)
        tc.variables["CMAKE_C_FLAGS"] = "-fno-integrated-as"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["isal_crypto"]
        self.cpp_info.set_property("cmake_file_name", "ISALCrypto")
        self.cpp_info.set_property("cmake_target_name", "ISALCrypto::isal_crypto")
        self.cpp_info.set_property("pkg_config_name", "libisal_crypto")
