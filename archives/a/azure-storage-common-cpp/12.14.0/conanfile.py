#!/usr/bin/env python3
"""Conan recipe for azure-storage-common-cpp 12.14.0.

Microsoft Azure Common Storage SDK for C++ — common abstractions for
Azure Storage client libraries (blobs, files, queues, etc.).

Build system: CMake (C++14, MIT license).
OHOS notes: C++17 via clang15, requires azure-core-cpp, libxml2, openssl.
"""

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.build import check_min_cppstd
import os


class AzureStorageCommonCppConan(ConanFile):
    name = "azure-storage-common-cpp"
    version = "12.14.0"
    description = "Microsoft Azure Common Storage SDK for C++ — common abstractions for Azure Storage client libraries"
    license = "MIT"
    homepage = "https://github.com/Azure/azure-sdk-for-cpp/tree/main/sdk/storage/azure-storage-common"
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
        self.requires("libxml2/2.15.3.1")
        self.requires("openssl/3.5.6")

    def validate(self):
        check_min_cppstd(self, 14)

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="azure-storage-common_12.14.0.tar.gz")

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
        cmake.configure(build_script_folder="sdk/storage/azure-storage-common")
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["azure-storage-common"]
        self.cpp_info.set_property("cmake_file_name", "azure-storage-common")
        self.cpp_info.set_property("cmake_target_name", "Azure::azure-storage-common")