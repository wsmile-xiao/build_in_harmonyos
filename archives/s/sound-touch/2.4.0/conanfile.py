#!/usr/bin/env python3
"""Conan recipe — SoundTouch 2.4.0 (CMake project).

SoundTouch is an open-source audio processing library for changing
the tempo, pitch, and playback rate of audio streams independently.

Source: https://www.surina.net/soundtouch/
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class SoundTouchConan(ConanFile):
    name = "sound-touch"
    version = "2.4.0"
    description = "Open-source audio processing library for tempo, pitch, and rate adjustment"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.surina.net/soundtouch/"
    url = "https://www.surina.net/soundtouch/"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

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
        # Disable NEON optimizations (ref: E099)
        tc.cache_variables["NEON"] = "OFF"
        # Add clang_rt.builtins for __powidf2 symbol (ref: E098)
        tc.cache_variables["CMAKE_EXE_LINKER_FLAGS"] = "-lclang_rt.builtins"
        tc.cache_variables["CMAKE_SHARED_LINKER_FLAGS"] = "-lclang_rt.builtins"
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
        self.cpp_info.libs = ["SoundTouch"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "SoundTouch")
        self.cpp_info.set_property("cmake_target_name", "SoundTouch::SoundTouch")
        self.cpp_info.set_property("pkg_config_name", "soundtouch")
