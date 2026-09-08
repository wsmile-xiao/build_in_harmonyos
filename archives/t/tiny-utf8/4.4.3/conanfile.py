#!/usr/bin/env python3
"""Conan recipe for tiny-utf8 4.4.3 — header-only Unicode (UTF-8) capable std::string.

tiny-utf8 is a single-header C++11 library (include/tinyutf8/tinyutf8.h).
Upstream CMake exposes an INTERFACE target `tinyutf8` (alias `tinyutf8::tinyutf8`)
with `cxx_std_11` compile feature and installs include/tinyutf8 plus a CMake
package config under ${CMAKE_INSTALL_DATAROOTDIR}/tinyutf8/cmake. No library
compilation is needed; the recipe copies the public header into the package.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.layout import basic_layout


class Tinyutf8Conan(ConanFile):
    name = "tiny-utf8"
    version = "4.4.3"
    description = "Unicode (UTF-8) capable std::string — header-only C++11 library"
    license = "MIT"
    homepage = "https://github.com/DuffsDevice/tiny-utf8"
    url = "https://github.com/DuffsDevice/tiny-utf8"
    topics = ("utf-8", "unicode", "string", "header-only", "cpp11")

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        # Official GitHub archive (tag v4.4.3) extracts to tiny-utf8-4.4.3/;
        # strip_root collapses it. SHA-256 verified in conandata.yml.
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Header-only: nothing to compile. Patches (if any) still apply.
        apply_conandata_patches(self)

    def package(self):
        # Mirror upstream install(DIRECTORY include/tinyutf8 -> include)
        copy(
            self,
            "tinyutf8.h",
            src=os.path.join(self.source_folder, "include", "tinyutf8"),
            dst=os.path.join(self.package_folder, "include", "tinyutf8"),
        )
        copy(
            self,
            "LICENCE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        # Mirror the upstream CMake package layout so consumers can use
        # find_package(tinyutf8) + tinyutf8::tinyutf8.
        self.cpp_info.set_property("cmake_file_name", "tinyutf8")
        self.cpp_info.set_property("cmake_target_name", "tinyutf8::tinyutf8")
        self.cpp_info.set_property("cmake_build_modules", [])
