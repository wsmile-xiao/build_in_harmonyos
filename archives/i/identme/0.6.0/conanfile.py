#!/usr/bin/env python3
"""Conan recipe for identme 0.6.0 — CMake project (CLI tool for public IP lookup).

Build system: CMake (C++17), uses system libcurl.
R26: Terminal tools must be statically linked (BUILD_SHARED_LIBS=OFF).
E092: CMake doesn't recognize HarmonyOS, force CMAKE_SYSTEM_NAME=Linux.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, save, load, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class IdentmeConan(ConanFile):
    name = "identme"
    version = "0.6.0"
    description = "Public IP address lookup"
    license = "0BSD"
    homepage = "https://ident.me"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # The CMakeLists.txt is in the cli/ subdirectory of the tarball.
        # Move cli/ contents to source root so cmake_layout can find CMakeLists.txt.
        cli_dir = os.path.join(self.source_folder, "cli")
        if os.path.isdir(cli_dir):
            for item in os.listdir(cli_dir):
                src = os.path.join(cli_dir, item)
                dst = os.path.join(self.source_folder, item)
                if not os.path.exists(dst):
                    shutil.move(src, dst)
            shutil.rmtree(cli_dir, ignore_errors=True)
        # R26: Patch CMakeLists.txt for static linking of curl deps and libc++
        cmake_path = os.path.join(self.source_folder, "CMakeLists.txt")
        content = load(self, cmake_path)
        content = content.replace(
            '    target_link_libraries(identme PRIVATE CURL::libcurl)\n    include_directories(${CURL_INCLUDE_DIRS})',
            '    target_link_libraries(identme PRIVATE CURL::libcurl)\n    target_link_libraries(identme PRIVATE /storage/Users/currentUser/usr/local/lib/libssl.a /storage/Users/currentUser/usr/local/lib/libcrypto.a /storage/Users/currentUser/usr/local/lib/libz.a)\n    include_directories(${CURL_INCLUDE_DIRS})'
        )
        content = content.replace(
            '    target_compile_options(identme PRIVATE -Os -flto -s)\n    set(CMAKE_INTERPROCEDURAL_OPTIMIZATION TRUE)',
            '    target_compile_options(identme PRIVATE -Os -flto -s)\n    target_link_options(identme PRIVATE -static-libstdc++)\n    set(CMAKE_INTERPROCEDURAL_OPTIMIZATION TRUE)'
        )
        save(self, cmake_path, content)

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: CMake doesn't recognize HarmonyOS, force Linux platform
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # R26: Terminal tools must be statically linked
        tc.cache_variables["BUILD_SHARED_LIBS"] = "OFF"
        # R26: Force static libcurl (bypass FindCURL picking up .so via pkg-config)
        tc.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_PkgConfig"] = "ON"
        tc.cache_variables["CURL_LIBRARY"] = "/storage/Users/currentUser/usr/local/lib/libcurl.a"
        tc.cache_variables["CURL_INCLUDE_DIR"] = "/storage/Users/currentUser/usr/local/include"
        # Library search path for curl static deps (ssl, crypto, z)
        tc.cache_variables["CMAKE_PREFIX_PATH"] = "/storage/Users/currentUser/usr/local"
        tc.cache_variables["CMAKE_EXE_LINKER_FLAGS"] = "-L/storage/Users/currentUser/usr/local/lib"
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
        self.cpp_info.libs = ["identme"]
