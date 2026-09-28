#!/usr/bin/env python3
"""Conan recipe for easyhttpcpp 2.1.0 — Sony cross-platform HTTP client (CMake).

Build system: CMake. Depends on Poco (Net/NetSSL/Data/DataSQLite/Foundation/Crypto)
and OpenSSL. The upstream CMakeLists uses Find-module style variables, so the
exploration patch maps them to Conan CMakeDeps imported targets
(poco::poco / openssl::openssl). CMAKE_POLICY_VERSION_MINIMUM=3.5 keeps the
project's cmake_minimum_required(3.0) compatible with the CMake 4.x toolchain.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class EasyhttpcppConan(ConanFile):
    name = "easyhttpcpp"
    version = "2.1.0"
    description = "Cross-platform HTTP client library with response cache and connection pooling"
    license = "MIT"
    homepage = "https://github.com/sony/easyhttpcpp"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("poco/1.15.3")
        self.requires("openssl/3.5.6")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake 4.x removed compatibility with cmake_minimum_required < 3.5
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

        CMakeDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["easyhttp"]
        self.cpp_info.requires = ["poco::poco", "openssl::openssl"]
        self.cpp_info.set_property("cmake_file_name", "easyhttpcpp")
        self.cpp_info.set_property("cmake_target_name", "easyhttpcpp::easyhttp")