#!/usr/bin/env python3
"""Conan recipe for libspng 0.7.4.

libspng is a PNG library (BSD-2-Clause).
Homepage: https://libspng.org/
Upstream: https://github.com/randy408/libspng
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, copy
from conan.tools.layout import basic_layout
import os


class LibspngConan(ConanFile):
    name = "libspng"
    version = "0.7.4"
    description = "Simplified PNG library — reads and writes PNG files via spng API"
    license = "BSD-2-Clause"
    homepage = "https://libspng.org/"
    url = "https://github.com/randy408/libspng"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/[>=1.2.0]")

    def layout(self):
        # Use basic_layout: source=. build=build/ (separate from source).
        # cmake_layout sets CMAKE_INSTALL_PREFIX=source_folder which breaks CMakeDeps.
        basic_layout(self)
        self.folders.build = "build"
        self.folders.generators = "build/generators"

    def source(self):
        get(self, **self.conan_data["sources"][0], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_INSTALL_PREFIX"] = self.package_folder
        tc.variables["SPNG_SHARED"] = self.options.shared
        tc.variables["SPNG_STATIC"] = not self.options.shared
        tc.variables["BUILD_EXAMPLES"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # CMake installs static target as libspng_static.a (lowercase).
        # Rename to libspng.a so consumers linking libs=["spng"] find it.
        lib_dir = os.path.join(self.package_folder, "lib")
        for src_name in ("libspng_STATIC.a", "libspng_static.a"):
            src = os.path.join(lib_dir, src_name)
            if os.path.exists(src):
                os.rename(src, os.path.join(lib_dir, "libspng.a"))
                break

    def package_info(self):
        self.cpp_info.libs = ["spng"]
        self.cpp_info.set_property("cmake_file_name", "spng")
        self.cpp_info.set_property("cmake_target_name", "spng::spng")
