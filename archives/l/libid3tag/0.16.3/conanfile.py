#!/usr/bin/env python3
"""Conan recipe for libid3tag 0.16.3 — CMake.

libid3tag is an ID3 tag parsing and manipulation library for MP3 files.
Depends on zlib for compressed ID3v2 frames.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import get, replace_in_file


class Libid3tagConan(ConanFile):
    name = "libid3tag"
    version = "0.16.3"
    description = "ID3 tag parsing and manipulation library for MP3 files."
    license = "GPL-2.0-or-later"
    homepage = "https://codeberg.org/tenacity/libid3tag"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
    }
    default_options = {
        "shared": False,
    }

    def requirements(self):
        self.requires("zlib/1.3.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        # CMake 4.x compatibility: project declares cmake_minimum_required(3.1)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # Upstream CMakeLists links ZLIB::ZLIB; the Conan zlib recipe
        # (CMakeDeps generator name zlib::zlib) provides the target.
        if not self.options.shared:
            tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.generate()

    def build(self):
        # Upstream CMakeLists links "ZLIB::ZLIB", but the Conan zlib recipe
        # (CMakeDeps) exports the target "zlib::zlib". Fix in build(), not
        # via patch — this is a Conan-integration detail, not an upstream bug.
        replace_in_file(self, os.path.join(self.source_folder, "CMakeLists.txt"),
                        "ZLIB::ZLIB", "zlib::zlib")
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["id3tag"]
        self.cpp_info.requires = ["zlib::zlib"]
