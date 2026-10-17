#!/usr/bin/env python3
"""Conan recipe for librdkafka — Apache Kafka C/C++ client library.

Build system: CMake (CMakeLists.txt in source root).
Dependencies: openssl, zlib, zstd, libcurl, cjson, lz4.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, rmdir
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibrdkafkaConan(ConanFile):
    name = "librdkafka"
    version = "2.5.3"
    description = "Apache Kafka C/C++ client library"
    license = "BSD-2-Clause"
    homepage = "https://github.com/confluentinc/librdkafka"
    url = ""

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.5.6")
        self.requires("zlib/1.3.1.1")
        self.requires("zstd/1.5.6")
        self.requires("libcurl/8.5.0")
        self.requires("cjson/1.7.19")
        self.requires("lz4/1.10.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["RDKAFKA_BUILD_STATIC"] = not self.options.shared
        tc.variables["RDKAFKA_BUILD_EXAMPLES"] = False
        tc.variables["RDKAFKA_BUILD_TESTS"] = False
        # Explicitly enable all features
        tc.variables["WITH_ZLIB"] = True
        tc.variables["WITH_CURL"] = True
        tc.variables["WITH_ZSTD"] = True
        tc.variables["WITH_SSL"] = True
        tc.variables["ENABLE_LZ4_EXT"] = True
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Remove cmake config files and pkg-config files we don't need
        rmdir(self, self.package_path / "lib" / "cmake")
        rmdir(self, self.package_path / "lib" / "pkgconfig")

    def package_info(self):
        self.cpp_info.libs = ["rdkafka"]
        if not self.options.shared:
            self.cpp_info.defines.append("LIBRDKAFKA_STATICLIB")
        self.cpp_info.set_property("cmake_file_name", "librdkafka")
        self.cpp_info.set_property("cmake_target_name", "librdkafka::librdkafka")
