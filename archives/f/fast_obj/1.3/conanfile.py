#!/usr/bin/env python3
"""Conan recipe — fast_obj 1.3 (CMake, single-header + static C library).

fast_obj is a single-file Wavefront OBJ parser. Upstream CMakeLists.txt only
defines an INTERFACE target `fast_obj` and a STATIC target `fast_obj_lib`
with NO install() rules, so packaging copies the header and the built static
archive manually (same pattern as f3/FMILibrary recipes).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class FastobjConan(ConanFile):
    name = "fast_obj"
    version = "1.3"
    description = "Fast single-file Wavefront OBJ parser for C/C++"
    license = "MIT"
    homepage = "https://github.com/thisistherk/fast_obj"
    url = ""  # CI fills this

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

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: keep static for system-name conflict safety
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Upstream CMakeLists.txt declares CMAKE_MINIMUM_REQUIRED(VERSION 3.0)
        # as its first line, which CMake >= 4.x rejects unless the policy floor
        # is lifted. Must be a cache variable (-D...) so it is set before the
        # CMakeLists.txt is parsed (toolchain-file variables load too late).
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # Upstream test app needs an external .obj file argument and pulls in
        # tiny_obj_loader.h; consumer-side coverage lives in test_package.
        tc.variables["FAST_OBJ_BUILD_TEST"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        # Upstream CMakeLists.txt has no install() rule: copy artifacts manually.
        copy(self, "fast_obj.h",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        build_dir = self.build_folder
        # CMake output name for target fast_obj_lib (static): libfast_obj_lib.a
        copy(self, "libfast_obj_lib.a",
             src=build_dir,
             dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["fast_obj_lib"]