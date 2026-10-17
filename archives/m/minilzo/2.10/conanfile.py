#!/usr/bin/env python3
"""Conan recipe for the standalone MiniLZO library."""
import os

from conan import ConanFile
from conan.tools.files import get, save, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class MinilzoConan(ConanFile):
    name = "minilzo"
    version = "2.10"
    description = "A small, self-contained LZO1X compression library"
    license = "GPL-2.0-or-later"
    homepage = "https://www.oberhumer.com/opensource/lzo/"
    url = "https://www.oberhumer.com/opensource/lzo/"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if str(self.settings.os) in ("Linux", "OHOS"):
            # The available CMake distribution has no OHOS platform module.
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["BUILD_SHARED_LIBS"] = False
        tc.user_presets_path = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        save(self, os.path.join(self.source_folder, "CMakeLists.txt"), """cmake_minimum_required(VERSION 3.15)\nproject(minilzo C)\nadd_library(minilzo STATIC minilzo/minilzo.c)\ntarget_include_directories(minilzo PUBLIC minilzo include/lzo)\nadd_executable(testmini minilzo/testmini.c)\ntarget_link_libraries(testmini PRIVATE minilzo)\nenable_testing()\nadd_test(NAME testmini COMMAND testmini)\ninstall(TARGETS minilzo ARCHIVE DESTINATION lib)\ninstall(DIRECTORY include/lzo DESTINATION include)\ninstall(FILES minilzo/minilzo.h DESTINATION include)\n""")
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["minilzo"]
        self.cpp_info.includedirs = ["include", "include/lzo"]
