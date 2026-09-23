#!/usr/bin/env python3
"""Conan recipe — rapidobj 1.1 (header-only C++17 library, nothing to compile).

rapidobj is a header-only C++17 OBJ/MTL parser. Upstream provides a CMake
INTERFACE target; packaging only installs include/rapidobj/rapidobj.hpp.
No third-party dependencies (fast_float / earcut are embedded in the header).

Reference: archives/t/tsl-ordered-map/ header-only CMake pattern.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches


class RapidobjConan(ConanFile):
    name = "rapidobj"
    version = "1.1"
    description = "Header-only C++17 library for parsing Wavefront OBJ/MTL files with focus on speed"
    license = "MIT"
    homepage = "https://github.com/guybrush77/rapidobj"
    url = "https://github.com/guybrush77/rapidobj"

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Header-only library: nothing to compile. Patches (if any) are
        # applied here so the packaged headers reflect adapted sources.
        apply_conandata_patches(self)

    def package(self):
        include_src = os.path.join(self.source_folder, "include")
        include_dst = os.path.join(self.package_folder, "include")
        copy(self, pattern="rapidobj/rapidobj.hpp", src=include_src, dst=include_dst)

    def package_info(self):
        # Header-only: no link libraries, no bin/lib dirs.
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        # Upstream CMakeLists.txt exports an INTERFACE target `rapidobj`.
        self.cpp_info.set_property("cmake_file_name", "RapidObj")
        self.cpp_info.set_property("cmake_target_name", "rapidobj::rapidobj")