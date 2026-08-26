#!/usr/bin/env python3
"""Conan recipe for azure-identity-cpp 1.13.3.

Microsoft Azure Identity SDK for C++ — authentication credential providers
for the Azure SDK client libraries (client secret, default azure credential,
chained token credential, etc.).

Build system: CMake (C++14, MIT license).
OHOS notes: C++17 via clang15, requires azure-core-cpp and openssl.
"""

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.build import check_min_cppstd
import os


class AzureIdentityCppConan(ConanFile):
    name = "azure-identity-cpp"
    version = "1.13.3"
    description = "Microsoft Azure Identity SDK for C++ — authentication credential providers for Azure SDK client libraries"
    license = "MIT"
    homepage = "https://github.com/Azure/azure-sdk-for-cpp/tree/main/sdk/identity/azure-identity"
    url = "https://github.com/Azure/azure-sdk-for-cpp"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("azure-core-cpp/1.16.4")
        self.requires("openssl/3.5.6")

    def validate(self):
        check_min_cppstd(self, 14)

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="azure-identity_1.13.3.tar.gz")

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["AZ_ALL_LIBRARIES"] = "OFF"
        tc.variables["WARNINGS_AS_ERRORS"] = "OFF"
        # OHOS: use C++17 (clang15 default)
        tc.variables["CMAKE_CXX_STANDARD"] = "17"
        # OHOS: CMake has no Platform/HarmonyOS.cmake → SONAME flags empty
        if self.settings.os == "OHOS":
            for lang in ("C", "CXX"):
                tc.variables[f"CMAKE_SHARED_LIBRARY_SONAME_{lang}_FLAG"] = "-Wl,-soname,"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(build_script_folder="sdk/identity/azure-identity")
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["azure-identity"]
        self.cpp_info.set_property("cmake_file_name", "azure-identity")
        self.cpp_info.set_property("cmake_target_name", "Azure::azure-identity")
        # Propagate transitive dependencies so consumers' CMakeDeps sets
        # CMAKE_PREFIX_PATH for azure-core/openssl, enabling the installed
        # azure-identity headers (azure/core/credentials/credentials.hpp)
        # to be found when building consumers.
        self.cpp_info.requires = ["azure-core-cpp::azure-core-cpp", "openssl::openssl"]