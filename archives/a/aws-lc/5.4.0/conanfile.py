#!/usr/bin/env python3
"""Conan recipe for aws-lc (AWS libcrypto) — CMake build system.

aws-lc is a general-purpose cryptographic library maintained by the AWS
Cryptography team, forked from BoringSSL. It provides libcrypto and libssl
as drop-in replacements for OpenSSL.

This recipe enforces R26: BUILD_SHARED_LIBS=OFF (system-name libraries
must be static to avoid polluting /lib).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class AwsLcConan(ConanFile):
    name = "aws-lc"
    version = "5.4.0"
    description = "AWS libcrypto (AWS-LC) — general-purpose cryptographic library forked from BoringSSL"
    license = "OpenSSL-SSLeay"
    homepage = "https://github.com/aws/aws-lc"
    url = "https://github.com/aws/aws-lc"  # CI this

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
        # R26: System-name libraries (libcrypto/libssl) must be static
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # DISABLE_GO: Go is not available on HarmonyOS
        tc.variables["DISABLE_GO"] = "ON"
        # Disable test executables (C++ linking issues on HarmonyOS)
        tc.variables["BUILD_TESTING"] = "OFF"
        # Disable bssl tool (library-only build)
        tc.variables["BUILD_TOOL"] = "OFF"
        # OPENSSL_NO_ASM: CMake on HarmonyOS reports CMAKE_SYSTEM_PROCESSOR as
        # "unknown" (uname -p returns "unknown"), so aws-lc falls back to ARCH
        # "generic" without defining OPENSSL_NO_ASM. This leaves assembly symbol
        # references unresolved at link time. Setting OPENSSL_NO_ASM=ON properly
        # enables pure-C fallback implementations.
        if self.settings.os == "OHOS":
            tc.variables["OPENSSL_NO_ASM"] = "ON"
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
        self.cpp_info.libs = ["crypto", "ssl"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "dl", "rt"]
