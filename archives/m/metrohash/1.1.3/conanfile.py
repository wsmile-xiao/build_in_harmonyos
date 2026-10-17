#!/usr/bin/env python3
"""Conan recipe — metrohash 1.1.3 (non-cryptographic hash library).

MetroHash by J. Andrew Rogers — 64/128-bit non-cryptographic hashes.
The 1.1.3 tarball ships no build system and no test program (only sources
plus the official verification vectors in src/testvector.h); this recipe
compiles the two portable translation units (metrohash64.cpp,
metrohash128.cpp) with a recipe-provided CMakeLists.txt.

Note: metrohash128crc.cpp/h implement the CRC variants with x86 SSE4.2
intrinsics (_mm_crc32_u64) and cannot be built on aarch64, so the CRC
translation unit is not part of this package (documented in notes.md).
"""
import os
import textwrap

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches, save


class MetroHashConan(ConanFile):
    name = "metrohash"
    version = "1.1.3"
    description = "MetroHash — a set of state-of-the-art non-cryptographic hash functions"
    license = "Apache-2.0"
    homepage = "https://github.com/jandrewrogers/MetroHash"
    url = "https://github.com/jandrewrogers/MetroHash"
    topics = ("hash", "non-cryptographic", "64-bit", "128-bit")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # Upstream 1.1.3 ships no build system; compile the portable sources
        # with a recipe-provided CMakeLists.txt. The CRC translation unit is
        # x86-SSE4.2-only and is intentionally not built (see notes.md).
        cmake_lists = textwrap.dedent("""\
            cmake_minimum_required(VERSION 3.15)
            project(metrohash CXX)
            add_library(metrohash ${METROHASH_SRC_DIR}/src/metrohash64.cpp
                                 ${METROHASH_SRC_DIR}/src/metrohash128.cpp)
            target_include_directories(metrohash PUBLIC ${METROHASH_SRC_DIR}/src)
        """)
        save(self, os.path.join(self.build_folder, "CMakeLists.txt"), cmake_lists)
        cmake = CMake(self)
        cmake.configure(variables={"METROHASH_SRC_DIR": self.source_folder},
                        build_script_folder=self.build_folder)
        cmake.build()

    def package(self):
        # Public headers; the umbrella metrohash.h also declares the x86-only
        # CRC functions (declarations only, harmless when unused).
        copy(self, "metrohash.h",
             src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "metrohash64.h",
             src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "metrohash128.h",
             src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "platform.h",
             src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "include"))
        # CRC 声明头必须随包：伞头 metrohash.h 无条件 include 它
        copy(self, "metrohash128crc.h",
             src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "*.a",
             src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"),
             keep_path=False)
        copy(self, "*.so*",
             src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"),
             keep_path=False)
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "metrohash")
        self.cpp_info.set_property("cmake_target_name", "metrohash::metrohash")
        self.cpp_info.libs = ["metrohash"]
