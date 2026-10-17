#!/usr/bin/env python3
"""Conan recipe for azure-core-cpp 1.16.4.

Azure Core SDK for C++ providing primitives, abstractions and helpers
for Azure SDK client libraries (HTTP, JSON, UUID, DateTime, etc.).

Build system: CMake (C++14, MIT license).
OHOS notes: C++17 via clang15, OpenSSL and curl required.
"""

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.build import check_min_cppstd
import os


class AzureCoreCppConan(ConanFile):
    name = "azure-core-cpp"
    version = "1.16.4"
    description = "Microsoft Azure Core SDK for C++ — primitives, abstractions and helpers for Azure SDK client libraries"
    license = "MIT"
    homepage = "https://github.com/Azure/azure-sdk-for-cpp/tree/main/sdk/core/azure-core"
    url = "https://github.com/Azure/azure-sdk-for-cpp"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "build_transport_curl": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "build_transport_curl": True,
        "fPIC": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("openssl/3.5.6")
        self.requires("libcurl/8.5.0")

    def validate(self):
        check_min_cppstd(self, 14)

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        # codeload.github.com returns tar.gz without .tar.gz extension;
        # specify filename explicitly so Conan's get() knows the format.
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="azure-core_1.16.4.tar.gz")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["BUILD_TRANSPORT_CURL"] = "ON" if self.options.build_transport_curl else "OFF"
        tc.variables["BUILD_WINHTTP"] = "OFF"
        tc.variables["DISABLE_RUST_IN_BUILD"] = "ON"
        tc.variables["DISABLE_AMQP"] = "ON"
        tc.variables["DISABLE_AZURE_CORE_OPENTELEMETRY"] = "ON"
        tc.variables["WARNINGS_AS_ERRORS"] = "OFF"
        # OHOS: use C++17 (clang15 default)
        tc.variables["CMAKE_CXX_STANDARD"] = "17"
        # OHOS: CMake has no Platform/HarmonyOS.cmake → SONAME flags empty
        # (E322-draft-F2BA). Manually set them like libcurl recipe does.
        if self.settings.os == "OHOS":
            for lang in ("C", "CXX"):
                tc.variables[f"CMAKE_SHARED_LIBRARY_SONAME_{lang}_FLAG"] = "-Wl,-soname,"
        # Pass cmake-modules path from the azure-sdk-for-cpp root
        # The archive root is the repo root; azure-core CMakeLists.txt
        # references ../../../cmake-modules from its sdk/core/azure-core/ location.
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # Build only the azure-core subproject. The repo-root CMakeLists.txt
        # would build the entire SDK tree (appconfiguration..tables), including
        # azure-core-amqp which fetches the Rust "corrosion" build tool via
        # FetchContent from GitHub (unreachable offline, and unnecessary).
        cmake.configure(build_script_folder="sdk/core/azure-core")
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["azure-core"]
        self.cpp_info.set_property("cmake_file_name", "azure-core")
        self.cpp_info.set_property("cmake_target_name", "Azure::azure-core")
        # Propagate transitive dependencies so consumers' CMakeDeps sets
        # CMAKE_PREFIX_PATH for openssl/libcurl, enabling the installed
        # azure-core-cppConfig.cmake's find_dependency(OpenSSL/CURL) calls.
        self.cpp_info.requires = ["libcurl::libcurl", "openssl::openssl"]