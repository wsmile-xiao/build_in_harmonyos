#!/usr/bin/env python3
"""Conan recipe — libobjc2 2.2.1 (GNUstep Objective-C runtime, CMake build).

Build notes:
  - libobjc2 2.2.1 uses CMake; the auto-generated autotools template was
    replaced with the CMake template.
  - tsl-robin-map is pulled via FetchContent when find_package fails. GitHub
    is unreachable on the OHOS build host, so the recipe downloads
    robin-map v1.2.1 explicitly and points FETCHCONTENT_SOURCE_DIR_ROBINMAP
    at the extracted sources (validated locally: cmake configure + make OK).
  - robin-map v1.2.1 declares cmake_minimum_required(VERSION 2.8), which
    CMake 4.x rejects; CMAKE_POLICY_VERSION_MINIMUM=3.5 is set in generate().
  - codeload URLs have no .tar.gz suffix, so explicit filename is required
    for get()/download() to detect the archive format.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, download, unzip
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
import os


class Libobjc2Conan(ConanFile):
    name = "libobjc2"
    version = "2.2.1"
    description = "GNUstep Objective-C runtime library"
    license = "MIT"
    homepage = "https://github.com/gnustep/libobjc2"
    url = "https://github.com/gnustep/libobjc2"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # tsl-robin-map: vendored via explicit download (GitHub unreachable on OHOS build host)
        robin = self.conan_data["robin_map"]
        robin_tar = os.path.join(self.source_folder, robin["filename"])
        download(self, robin["url"], robin_tar, sha256=robin["sha256"])
        # unzip keeps the top-level dir robin-map-1.2.1/ (FetchContent entry point)
        unzip(self, robin_tar, destination=self.source_folder)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: System-name libraries default to static
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # robin-map v1.2.1 requires old CMake policy version (validated locally)
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # Point FetchContent at the vendored robin-map sources (GitHub unreachable)
        tc.variables["FETCHCONTENT_SOURCE_DIR_ROBINMAP"] = os.path.join(self.source_folder, "robin-map-1.2.1")
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
        self.cpp_info.libs = ["objc"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_find_mode", "both")
