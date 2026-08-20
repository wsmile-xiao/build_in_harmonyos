#!/usr/bin/env python3
"""Conan recipe for libheif 1.22.2 — HEIF file format library.

All codecs disabled; provides HEIF container support only.
"""
from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibheifConan(ConanFile):
    name = "libheif"
    version = "1.22.2"
    description = "HEIF file format library (codec-free build)"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/strukturag/libheif"
    url = "https://github.com/strukturag/libheif"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["WITH_EXAMPLES"] = False
        tc.variables["WITH_GDK_PIXBUF"] = False
        tc.variables["BUILD_TESTING"] = False
        tc.variables["WITH_LIBDE265"] = False
        tc.variables["WITH_X265"] = False
        tc.variables["WITH_AOM_DECODER"] = False
        tc.variables["WITH_AOM_ENCODER"] = False
        tc.variables["WITH_X264"] = False
        tc.variables["WITH_DAV1D"] = False
        tc.variables["ENABLE_PLUGIN_LOADING"] = False
        tc.variables["WITH_LIBSHARPYUV"] = False
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
        self.cpp_info.libs = ["heif"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "libheif")
        self.cpp_info.set_property("cmake_target_name", "libheif::libheif")
        self.cpp_info.set_property("pkg_config_name", "libheif")
