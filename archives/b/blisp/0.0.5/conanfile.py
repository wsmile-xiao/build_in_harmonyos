#!/usr/bin/env python3
"""Conan recipe for blisp 0.0.5 (CMake build system).

Build system: CMake
Dependencies: vendored libserialport (serial port communication) — the GitHub
              tag tarball does not include git submodules, so libserialport is
              declared separately in conandata.yml and extracted into
              vendor/libserialport/ during source().
              argtable3 submodule is only needed for the CLI tool
              (BLISP_BUILD_CLI), which is disabled.
"""
import os

from conan import ConanFile
from conan.tools.files import (
    get, apply_conandata_patches, export_conandata_patches,
    rmdir, rm
)
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class BlispConan(ConanFile):
    name = "blisp"
    version = "0.0.5"
    description = "Bouffalo Labs ISP (in-system-programming) tool & library — open source tool to flash Bouffalo RISC-V MCUs"
    license = "MIT"
    homepage = "https://github.com/pine64/blisp"
    url = ""

    # 配方仅产出静态库 libblisp.a，package() 中已删除 .so/.dylib/.dll
    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        # Download blisp source
        get(self, **self.conan_data["sources"], strip_root=True)
        # Download libserialport submodule source and place it where
        # CMakeLists.txt expects it (vendor/libserialport/).
        get(self, **self.conan_data["libserialport"],
            destination=os.path.join(self.source_folder, "vendor", "libserialport"),
            strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Don't build the CLI tool — it needs the argtable3 submodule which
        # is not included in the tag tarball.
        tc.variables["BLISP_BUILD_CLI"] = False
        # Don't compile upstream tests — they use FetchContent to download
        # GoogleTest, which may be unavailable in the CI environment.
        tc.variables["COMPILE_TESTS"] = False
        # Use the vendored libserialport source (not a system install).
        tc.variables["BLISP_USE_SYSTEM_LIBRARIES"] = False
        tc.generate()

    def build(self):
        # apply_conandata_patches 自动应用 conandata.yml 中声明的补丁：
        #   0001: write_file() → file(WRITE) 修复 CMake 弃用
        #   0002: elseif(UNIX ...) → elseif(NOT WIN32 ...) 修复 OHOS 平台检测
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Remove the shared library to avoid .so pollution; keep only the
        # static archive (libblisp.a) for consumers.
        rm(self, "libblisp.so*", os.path.join(self.package_folder, "lib"))
        rm(self, "libblisp.dylib*", os.path.join(self.package_folder, "lib"))
        rm(self, "libblisp.dll*", os.path.join(self.package_folder, "bin"))
        # Remove CMake package config files — the recipe provides cpp_info.
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.libs = ["blisp"]
        self.cpp_info.includedirs = ["include"]
