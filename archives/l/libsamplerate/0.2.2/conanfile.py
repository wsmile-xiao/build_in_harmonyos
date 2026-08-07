#!/usr/bin/env python3
"""Conan recipe for libsamplerate 0.2.2 (CMake build system)."""

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibsamplerateConan(ConanFile):
    name = "libsamplerate"
    version = "0.2.2"
    description = "Audio sample rate conversion library"
    license = "BSD-2-Clause"
    homepage = "https://libsndfile.github.io/libsamplerate/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

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
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["samplerate"]
        self.cpp_info.set_property("cmake_file_name", "libsamplerate")
        self.cpp_info.set_property("cmake_target_name", "libsamplerate::libsamplerate")
