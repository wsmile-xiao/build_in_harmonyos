#!/usr/bin/env python3
"""Conan recipe — OpenJPEG (CMake).

OpenJPEG is an open-source JPEG 2000 codec library.
Build system: CMake.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class OpenjpegConan(ConanFile):
    name = "openjpeg"
    version = "2.5.4"
    description = "Open-source JPEG 2000 codec library"
    license = "BSD-2-Clause"
    homepage = "https://github.com/uclouvain/openjpeg"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "build_codec": [True, False],
    }
    default_options = {
        "shared": True,
        "build_codec": True,
    }

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
        tc.variables["BUILD_STATIC_LIBS"] = "OFF" if self.options.shared else "ON"
        tc.variables["BUILD_CODEC"] = "ON" if self.options.build_codec else "OFF"
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["BUILD_DOC"] = "OFF"
        # Fix SONAME on HarmonyOS (CMake doesn't recognize OHOS platform)
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        # RPATH for installed binaries
        tc.variables["CMAKE_SKIP_RPATH"] = "OFF"
        tc.variables["CMAKE_INSTALL_RPATH"] = "$ORIGIN/../lib"
        tc.variables["CMAKE_INSTALL_RPATH_USE_LINK_PATH"] = "ON"
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
        self.cpp_info.libs = ["openjp2"]
        self.cpp_info.set_property("cmake_file_name", "OpenJPEG")
        self.cpp_info.set_property("cmake_target_name", "OPENJPEG::OpenJPEG")
        self.cpp_info.includedirs = ["include/openjpeg-2.5"]
