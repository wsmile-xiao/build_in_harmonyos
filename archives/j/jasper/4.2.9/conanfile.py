#!/usr/bin/env python3
"""Conan recipe for JasPer 4.2.9 — CMake build system."""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout

class JasperConan(ConanFile):
    name = "jasper"
    version = "4.2.9"
    description = "JPEG-2000 codec implementation"
    license = "JasPer-2.0"
    homepage = "https://github.com/jasper-software/jasper"
    url = "https://github.com/jasper-software/jasper"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libjpeg/10")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["ALLOW_IN_SOURCE_BUILD"] = "ON"
        tc.cache_variables["JAS_STDC_VERSION"] = "201112L"
        tc.cache_variables["JAS_ENABLE_OPENGL"] = "OFF"
        tc.cache_variables["JAS_ENABLE_LIBHEIF"] = "OFF"
        tc.cache_variables["JAS_ENABLE_DOC"] = "OFF"
        tc.cache_variables["JAS_ENABLE_LIBJPEG"] = "ON"
        tc.cache_variables["JAS_INCLUDE_BMP_CODEC"] = "ON"
        tc.cache_variables["JAS_INCLUDE_JP2_CODEC"] = "ON"
        tc.cache_variables["JAS_INCLUDE_JPC_CODEC"] = "ON"
        tc.cache_variables["JAS_INCLUDE_JPG_CODEC"] = "ON"
        tc.cache_variables["JAS_INCLUDE_MIF_CODEC"] = "ON"
        tc.cache_variables["JAS_INCLUDE_PGX_CODEC"] = "ON"
        tc.cache_variables["JAS_INCLUDE_PNM_CODEC"] = "ON"
        tc.cache_variables["JAS_INCLUDE_RAS_CODEC"] = "ON"
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
        self.cpp_info.libs = ["jasper"]
