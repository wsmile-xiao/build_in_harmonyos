#!/usr/bin/env python3
"""Conan recipe — jwt-cpp 0.7.1 (CMake header-only / INTERFACE library).

Downstream expects:
  find_package(jwt-cpp REQUIRED)
  target_link_libraries(... PRIVATE jwt-cpp::jwt-cpp)

The upstream INTERFACE target transitively links OpenSSL::SSL + OpenSSL::Crypto,
so this recipe requires openssl and re-exports it through cpp_info.requires.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy


class JwtCppConan(ConanFile):
    name = "jwt-cpp"
    version = "0.7.1"
    description = "A header only library for creating and validating JSON Web Tokens in C++"
    license = "MIT"
    homepage = "https://github.com/Thalhammer/jwt-cpp"
    url = ""  # CI fills this

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # jwt-cpp is a header-only library that needs OpenSSL at consumption time
        self.requires("openssl/3.5.6.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # OHOS: CMake may not recognize OHOS as a known system name
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # Disable optional targets; we only install the header-only library
        tc.cache_variables["JWT_BUILD_EXAMPLES"] = "OFF"
        tc.cache_variables["JWT_BUILD_TESTS"] = "OFF"
        tc.cache_variables["JWT_BUILD_DOCS"] = "OFF"
        tc.cache_variables["JWT_ENABLE_COVERAGE"] = "OFF"
        tc.cache_variables["JWT_ENABLE_FUZZING"] = "OFF"
        tc.cache_variables["JWT_DISABLE_PICOJSON"] = "OFF"
        tc.cache_variables["JWT_DISABLE_BASE64"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Header-only: configure + install only (INTERFACE target, nothing to compile)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Header-only: no link libraries
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]

        self.cpp_info.set_property("cmake_file_name", "jwt-cpp")
        self.cpp_info.set_property("cmake_target_name", "jwt-cpp::jwt-cpp")
        self.cpp_info.set_property("pkg_config_name", "jwt-cpp")

        # Re-export OpenSSL so consumers get the crypto dependency transitively
        self.cpp_info.requires = ["openssl::openssl"]
