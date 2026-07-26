#!/usr/bin/env python3
"""Conan recipe for libreplaygain r475."""

import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibreplaygainConan(ConanFile):
    name = "libreplaygain"
    version = "r475"
    description = "Library to implement ReplayGain standard for audio"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.musepack.net/"
    url = homepage
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
        replace_in_file(
            self,
            os.path.join(self.source_folder, "CMakeLists.txt"),
            "CMAKE_MINIMUM_REQUIRED(VERSION 2.4)",
            "CMAKE_MINIMUM_REQUIRED(VERSION 3.5)",
        )
        replace_in_file(
            self,
            os.path.join(self.source_folder, "src", "CMakeLists.txt"),
            "add_library(replaygain-static STATIC gain_analysis)\n"
            "set_target_properties(replaygain-static PROPERTIES OUTPUT_NAME replaygain CLEAN_DIRECT_OUTPUT 1)\n"
            "\n"
            "add_library(replaygain-shared SHARED gain_analysis)\n"
            "set_target_properties(replaygain-shared PROPERTIES OUTPUT_NAME replaygain CLEAN_DIRECT_OUTPUT 1 VERSION 1.0.0 SOVERSION 1)\n"
            "\n"
            'install(TARGETS replaygain-static replaygain-shared LIBRARY DESTINATION "lib${LIB_SUFFIX}" ARCHIVE DESTINATION "lib${LIB_SUFFIX}")',
            "add_library(replaygain gain_analysis)\n"
            "set_target_properties(replaygain PROPERTIES OUTPUT_NAME replaygain CLEAN_DIRECT_OUTPUT 1)\n"
            "if(BUILD_SHARED_LIBS)\n"
            "    set_target_properties(replaygain PROPERTIES VERSION 1.0.0 SOVERSION 1)\n"
            "endif()\n"
            "\n"
            'install(TARGETS replaygain LIBRARY DESTINATION "lib${LIB_SUFFIX}" ARCHIVE DESTINATION "lib${LIB_SUFFIX}")',
        )

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "gain_analysis.h",
            src=os.path.join(self.source_folder, "include", "replaygain"),
            dst=os.path.join(self.package_folder, "include", "replaygain"),
        )

    def package_info(self):
        self.cpp_info.libs = ["replaygain"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("cmake_file_name", "libreplaygain")
        self.cpp_info.set_property("cmake_target_name", "libreplaygain::libreplaygain")
