#!/usr/bin/env python3
"""Conan recipe — libsnd 0.1.1 (CMake project, static DSP library).

Upstream: https://github.com/everdrone/libsnd
CMakeLists.txt builds a STATIC archive named `libsnd.a` (PREFIX ""),
installs include/snd.h + CMake package config. BUILD_TESTS is disabled
here (upstream downloads googletest@master via ExternalProject at
configure time, which is not suitable for the packaged build); upstream
unit tests are enumerated and run separately in the adaptation workflow.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibsndConan(ConanFile):
    name = "libsnd"
    version = "0.1.1"
    description = "Digital Signal Processing Library and Audio Toolbox for the Modern Synthesist"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/everdrone/libsnd"
    url = "https://github.com/everdrone/libsnd"

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
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_TESTS"] = "OFF"
        # Upstream declares cmake_minimum_required(3.2.2); CMake >= 3.5 removed
        # compatibility with older minimums, so relax the policy floor.
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
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
        # Upstream sets PREFIX "" on the libsnd target, so the packaged
        # archive is `libsnd.a` (no extra "lib" prefix); CMakeDeps resolves
        # lib<name>.a, hence the libs entry is "snd".
        self.cpp_info.libs = ["snd"]