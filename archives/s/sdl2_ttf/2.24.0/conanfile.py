#!/usr/bin/env python3
"""Conan recipe — sdl2_ttf 2.24.0 (SDL2 TrueType font rendering library).

Build system: CMake (upstream ships CMakeLists.txt + autotools; CMake
preferred for conan integration — consistent with sdl2/sdl2_image family).

Patch 0001: switches find_package(Freetype) / Freetype::Freetype (CMake
FindFreetype module names) to find_package(freetype CONFIG) /
freetype::freetype to match the ohpcd freetype package's CMakeDeps targets.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class Sdl2TtfConan(ConanFile):
    name = "sdl2_ttf"
    version = "2.24.0"
    description = "SDL2 TrueType font rendering library"
    license = "MIT"
    homepage = "https://github.com/libsdl-org/SDL_ttf"
    url = ""

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("sdl2/2.30.10")
        self.requires("freetype/2.14.3.1")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        # Deliberately do NOT set cmake_file_name for sdl2: the default
        # generates sdl2-config.cmake with lowercase variables
        # (sdl2_INCLUDE_DIR), which do NOT clobber the uppercase
        # SDL2_INCLUDE_DIR cache variable that PrivateSDL2's find_path
        # sets. Setting cmake_file_name="SDL2" would generate
        # SDL2Config.cmake with SDL2_INCLUDE_DIR (uppercase) that
        # shadows the cache var, causing file(READ SDL_version.h) to
        # look in include/ instead of include/SDL2/.
        deps.generate()
        tc = CMakeToolchain(self)
        tc.cache_variables["SDL2TTF_VENDORED"] = "OFF"
        tc.cache_variables["SDL2TTF_HARFBUZZ"] = "OFF"
        tc.cache_variables["SDL2TTF_SAMPLES"] = "OFF"
        tc.cache_variables["SDL2TTF_INSTALL"] = "ON"
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
        self.cpp_info.set_property("cmake_file_name", "SDL2_ttf")
        self.cpp_info.set_property("cmake_target_name", "SDL2_ttf::SDL2_ttf")
        self.cpp_info.set_property("pkg_config_name", "SDL2_ttf")
        self.cpp_info.libs = ["SDL2_ttf"]
        self.cpp_info.requires = ["sdl2::sdl2", "freetype::freetype"]
        self.cpp_info.includedirs = ["include/SDL2", "include"]
        sdl2 = self.dependencies["sdl2"]
        if sdl2.package_folder:
            self.cpp_info.includedirs.append(
                os.path.join(sdl2.package_folder, "include/SDL2"))
