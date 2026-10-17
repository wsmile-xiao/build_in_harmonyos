#!/usr/bin/env python3
"""Conan recipe for jeolib-miallib 1.1.7 (CMake, C image-processing library).

Upstream: https://github.com/ec-jrc/jeolib-miallib (JRC miallib)

Dependencies (all published in the ohpcd registry):
  zlib, gdal, libtiff, libgeotiff, proj, fftw, gsl, shapelib/1.5.0

Adaptation notes (see notes.md):
  - PROCESS_IN_PARALLEL=OFF: upstream parallel branch requires the
    OpenMP::OpenMP_CXX target, but the project is C-only (project(miallib)),
    so find_package(OpenMP) would fail / target undefined. Serial build.
  - projection.c dropped by patch: legacy PROJ4 API (pj_init/pj_transform),
    incompatible with PROJ >= 6, no callers elsewhere in the tree.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class MiallibConan(ConanFile):
    name = "jeolib-miallib"
    version = "1.1.7"
    description = "JRC miallib: morphological image processing library (C)"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/ec-jrc/jeolib-miallib"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1.1")
        self.requires("gdal/3.9.2.3")
        self.requires("libtiff/4.7.2")
        self.requires("libgeotiff/1.7.4")
        self.requires("proj/9.3.1.1")
        self.requires("fftw/3.3.11")
        self.requires("gsl/2.7")
        self.requires("shapelib/1.5.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake >= 4 removed compatibility with cmake_minimum_required < 3.5
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Serial build: upstream parallel branch needs OpenMP::OpenMP_CXX in a
        # C-only project (see notes.md)
        tc.variables["PROCESS_IN_PARALLEL"] = "OFF"
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
        self.cpp_info.set_property("cmake_file_name", "miallib")
        self.cpp_info.set_property("cmake_target_name", "miallib::miallib")
        self.cpp_info.set_property("pkg_config_name", "miallib")
        self.cpp_info.libs = ["miallib"]
        # headers are installed into <prefix>/include/miallib/
        self.cpp_info.includedirs = ["include/miallib"]
