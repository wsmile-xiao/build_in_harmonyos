#!/usr/bin/env python3
"""Conan recipe for n2n 3.1.1 — Peer-to-peer VPN.

n2n is a layer-2 peer-to-peer VPN by ntop. It builds:
  - libn2n.a (static library)
  - edge (VPN client, installed to sbin)
  - supernode (VPN coordinator, installed to sbin)
  - n2n-benchmark (benchmarking tool, installed to bin)

On OHOS, TUN/TAP is not available so edge's VPN tunnel is non-functional,
but supernode works fully. OpenSSL provides AES/ChaCha20 encryption.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class N2NConan(ConanFile):
    name = "n2n"
    version = "3.1.1"
    description = "Peer-to-peer VPN (layer-2) by ntop"
    license = "GPL-3.0"
    homepage = "https://github.com/ntop/n2n"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/1.1.1w")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Define __OHOS__ for platform-specific guards in patches (R32)
        if self.settings.os == "OHOS":
            tc.preprocessor_definitions["__OHOS__"] = "1"
        # CMake policy compatibility: n2n uses cmake_minimum_required(VERSION 2.6)
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # n2n-specific options
        tc.variables["N2N_OPTION_USE_OPENSSL"] = "ON"
        # pthread disabled: OHOS/musl does not implement pthread_cancel
        tc.variables["N2N_OPTION_USE_PTHREAD"] = "OFF"
        # Static library (n2n CMakeLists.txt uses add_library(n2n STATIC ...))
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
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
        self.cpp_info.libs = ["n2n"]
        self.cpp_info.bindirs = ["sbin", "bin"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.defines = ["CMAKE_BUILD"]
