#!/usr/bin/env python3
"""Conan recipe for poco 1.14.2 adapted for HarmonyOS PC (aarch64)."""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class PocoConan(ConanFile):
    name = "poco"
    version = "1.14.2"
    description = "C++ class libraries for building network-based applications"
    license = "BSL-1.0"
    homepage = "https://pocoproject.org"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "enable_data_sqlite": [True, False],
        "enable_data_mysql": [True, False],
        "enable_data_postgresql": [True, False],
        "enable_data_odbc": [True, False],
        "enable_mongodb": [True, False],
        "enable_redis": [True, False],
        "enable_prometheus": [True, False],
        "enable_jwt": [True, False],
        "enable_netssl": [True, False],
        "enable_crypto": [True, False],
        "enable_activerecord": [True, False],
        "enable_zip": [True, False],
        "enable_pagecompiler": [True, False],
    }
    default_options = {
        "shared": False,
        "enable_data_sqlite": True,
        "enable_data_mysql": False,
        "enable_data_postgresql": False,
        "enable_data_odbc": False,
        "enable_mongodb": True,
        "enable_redis": True,
        "enable_prometheus": True,
        "enable_jwt": True,
        "enable_netssl": True,
        "enable_crypto": True,
        "enable_activerecord": True,
        "enable_zip": True,
        "enable_pagecompiler": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.5.6")
        self.requires("zlib/1.3.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: CMake doesn't recognize HarmonyOS as a platform.
        # Set CMAKE_SYSTEM_NAME=Linux so UNIX/POSIX source files are included.
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.variables["CMAKE_BUILD_TYPE"] = "Release"
        # Disable tests and samples
        tc.variables["ENABLE_TESTS"] = "OFF"
        tc.variables["ENABLE_SAMPLES"] = "OFF"
        # Module options (no trimming — all available modules enabled)
        tc.variables["ENABLE_FOUNDATION"] = "ON"
        tc.variables["ENABLE_ENCODINGS"] = "ON"
        tc.variables["ENABLE_XML"] = "ON"
        tc.variables["ENABLE_JSON"] = "ON"
        tc.variables["ENABLE_UTIL"] = "ON"
        tc.variables["ENABLE_NET"] = "ON"
        tc.variables["ENABLE_DATA_SQLITE"] = self.options.enable_data_sqlite
        tc.variables["ENABLE_DATA_MYSQL"] = self.options.enable_data_mysql
        tc.variables["ENABLE_DATA_POSTGRESQL"] = self.options.enable_data_postgresql
        tc.variables["ENABLE_DATA_ODBC"] = self.options.enable_data_odbc
        tc.variables["ENABLE_MONGODB"] = self.options.enable_mongodb
        tc.variables["ENABLE_REDIS"] = self.options.enable_redis
        tc.variables["ENABLE_PROMETHEUS"] = self.options.enable_prometheus
        tc.variables["ENABLE_JWT"] = self.options.enable_jwt
        tc.variables["ENABLE_NETSSL"] = self.options.enable_netssl
        tc.variables["ENABLE_CRYPTO"] = self.options.enable_crypto
        tc.variables["ENABLE_ACTIVERECORD"] = self.options.enable_activerecord
        tc.variables["ENABLE_SEVENZIP"] = "OFF"
        tc.variables["ENABLE_ENCODINGS_COMPILER"] = "OFF"
        tc.variables["ENABLE_PDF"] = "OFF"
        tc.variables["ENABLE_DNSSD"] = "OFF"
        tc.variables["ENABLE_APACHECONNECTOR"] = "OFF"
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
        self.cpp_info.set_property("cmake_file_name", "Poco")
        self.cpp_info.set_property("cmake_target_name", "Poco::Poco")

        libs = [
            "PocoFoundation",
            "PocoEncodings",
            "PocoXML",
            "PocoJSON",
            "PocoUtil",
            "PocoNet",
            "PocoNetSSL",
            "PocoCrypto",
            "PocoJWT",
            "PocoData",
            "PocoDataSQLite",
            "PocoMongoDB",
            "PocoRedis",
            "PocoPrometheus",
            "PocoActiveRecord",
            "PocoZip",
        ]
        self.cpp_info.libs = libs
