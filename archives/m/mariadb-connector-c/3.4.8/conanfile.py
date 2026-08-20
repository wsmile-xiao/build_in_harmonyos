#!/usr/bin/env python3
"""Conan recipe for mariadb-connector-c 3.4.8 on OpenHarmony PC.

mariadb-connector-c is the MariaDB client library (libmariadb) that provides
client-side connectivity to MariaDB and MySQL servers. It is used as a
dependency by Qt SQL driver plugins (qt-mariadb) and other database tooling.
"""
import os
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class MariadbConnectorCConan(ConanFile):
    name = "mariadb-connector-c"
    version = "3.4.8"
    description = "MariaDB Connector/C — client library for MariaDB and MySQL"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/mariadb-corporation/mariadb-connector-c"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "with_ssl": [True, False],
    }
    default_options = {
        "shared": True,
        "with_ssl": True,
        "openssl/*:shared": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        if self.options.with_ssl:
            self.requires("openssl/3.5.6")

    def layout(self):
        cmake_layout(self)

    def validate(self):
        # R32: settings.os check must use in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"mariadb-connector-c only supports Linux and OHOS, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Position-independent code required for shared library
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = "ON"
        # Use bundled zlib (compiled with -fPIC) to avoid PIC relocation
        # errors when linking conan's static libz.a into libmariadb.so
        tc.variables["WITH_EXTERNAL_ZLIB"] = "OFF"
        # Disable unit tests
        tc.variables["WITH_UNIT_TESTS"] = "OFF"

        if self.options.with_ssl:
            openssl = self.dependencies["openssl"]
            openssl_inc = os.path.join(openssl.package_folder, "include")
            openssl_lib = os.path.join(openssl.package_folder, "lib")

            # The CMakeLists.txt calls FIND_PACKAGE(OpenSSL) and checks
            # OPENSSL_FOUND (uppercase).  Conan CMakeDeps only sets
            # openssl_FOUND (lowercase), so we pass the paths and the
            # found-flag directly via CMakeToolchain variables.
            tc.variables["WITH_SSL"] = "OPENSSL"
            tc.variables["OPENSSL_INCLUDE_DIR"] = openssl_inc
            tc.variables["OPENSSL_SSL_LIBRARY"] = os.path.join(openssl_lib, "libssl.a")
            tc.variables["OPENSSL_CRYPTO_LIBRARY"] = os.path.join(openssl_lib, "libcrypto.a")
            tc.variables["OPENSSL_FOUND"] = "TRUE"

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
        # Default install layout puts libs in lib/mariadb/ and headers in include/mariadb/
        self.cpp_info.libdirs = ["lib/mariadb"]
        self.cpp_info.includedirs = ["include/mariadb"]
        self.cpp_info.libs = ["mariadb"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "dl"]
