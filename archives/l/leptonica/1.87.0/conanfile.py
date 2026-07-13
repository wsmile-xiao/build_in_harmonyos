#!/usr/bin/env python3
"""Conan recipe — leptonica 1.87.0 (CMake build).

Built with CMake because autogen.sh fails (libtoolize shebang path error).
Dependencies: zlib (required, Conan), libpng/libjpeg/libtiff/openjpeg (optional, system).
"""
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LeptonicaConan(ConanFile):
    name = "leptonica"
    version = "1.87.0"
    description = "Open source library for image processing and image analysis"
    license = "BSD-2-Clause"
    homepage = "https://github.com/DanBloomberg/leptonica"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        copy(self, "conandata.yml", self.recipe_folder, self.export_sources_folder)

    def requirements(self):
        self.requires("zlib/1.3.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Build static library (leptonica is a library, not a terminal tool)
        tc.variables["BUILD_SHARED_LIBS"] = False
        # CMake policy: allow older cmake_minimum_required
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # Disable utility programs (we only need the library)
        tc.variables["BUILD_PROG"] = False
        # Disable optional image format libraries not managed by Conan
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_PNG"] = True
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_JPEG"] = True
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_TIFF"] = True
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_GIF"] = True
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_WebP"] = True
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_OpenJPEG"] = True
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
        self.cpp_info.libs = ["leptonica"]
        self.cpp_info.includedirs = ["include", "include/leptonica"]
        self.cpp_info.set_property("cmake_file_name", "Leptonica")
        self.cpp_info.set_property("pkg_config_name", "lept")
        # leptonica depends on zlib (Conan manages this via requires)
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
