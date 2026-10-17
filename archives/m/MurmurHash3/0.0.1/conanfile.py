#!/usr/bin/env python3
"""Conan recipe for MurmurHash3 0.0.1.

MurmurHash3 is a non-cryptographic hash function by Austin Appleby,
part of the SMHasher repository. The upstream CMakeLists.txt builds
all hash functions; this recipe replaces it to build only MurmurHash3.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, save, apply_conandata_patches, export_conandata_patches


class MurmurHash3Conan(ConanFile):
    name = "murmurhash3"
    version = "0.0.1"
    description = "MurmurHash3 non-cryptographic hash function by Austin Appleby"
    license = "Public Domain"
    homepage = "https://github.com/aappleby/smhasher"
    url = "https://github.com/aappleby/smhasher"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Replace upstream CMakeLists.txt to build only MurmurHash3
        cmake_content = """cmake_minimum_required(VERSION 3.15)
project(MurmurHash3 CXX)
set(CMAKE_CXX_STANDARD 17)

add_library(MurmurHash3 src/MurmurHash3.cpp)
target_include_directories(MurmurHash3 PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/src)

install(TARGETS MurmurHash3
    ARCHIVE DESTINATION lib
    LIBRARY DESTINATION lib
    RUNTIME DESTINATION bin)
install(FILES src/MurmurHash3.h DESTINATION include)
"""
        save(self, os.path.join(self.source_folder, "CMakeLists.txt"), cmake_content)

        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["MurmurHash3"]
