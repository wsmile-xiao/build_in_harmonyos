#!/usr/bin/env python3
"""Conan recipe for cassandra-cpp-driver 2.17.1.

DataStax C/C++ driver for Apache Cassandra.
Uses CMake build system with libuv, OpenSSL, and zlib dependencies.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout


class CassandraCppDriverConan(ConanFile):
    name = "cassandra-cpp-driver"
    version = "2.17.1"
    description = "DataStax C/C++ driver for Apache Cassandra"
    license = "Apache-2.0"
    homepage = "https://github.com/apache/cassandra-cpp-driver"
    url = "https://github.com/apache/cassandra-cpp-driver"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libuv/1.52.1")
        self.requires("openssl/3.5.6")
        self.requires("zlib/1.3.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CASS_BUILD_SHARED"] = "ON" if self.options.shared else "OFF"
        tc.variables["CASS_BUILD_STATIC"] = "OFF" if self.options.shared else "ON"
        tc.variables["CASS_INSTALL_HEADER"] = "ON"
        tc.variables["CASS_INSTALL_HEADER_IN_SUBDIR"] = "OFF"
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        if self.options.shared:
            self.cpp_info.libs = ["cassandra"]
        else:
            self.cpp_info.libs = ["cassandra_static"]
        self.cpp_info.set_property("cmake_file_name", "cassandra-cpp-driver")
        self.cpp_info.set_property("cmake_target_name", "cassandra-cpp-driver::cassandra")
        self.cpp_info.requires = ["libuv::libuv", "openssl::openssl", "zlib::zlib"]
        if not self.options.shared:
            self.cpp_info.system_libs = ["c++"]
