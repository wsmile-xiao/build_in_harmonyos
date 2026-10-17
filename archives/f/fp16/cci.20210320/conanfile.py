#!/usr/bin/env python3
"""Conan recipe — fp16 cci.20210320 (header-only library, nothing to compile).

FP16 provides header-only IEEE-754 half-precision (16-bit) <-> single-precision
conversion routines, including the ARM "alternative" half format and PSIMD
helpers. Upstream builds an INTERFACE (header-only) CMake target; package()
only installs the include/ headers.

Reference: archives/t/tsl-ordered-map/1.1.0/ (header-only CMake pattern).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches


class Fp16Conan(ConanFile):
    name = "fp16"
    version = "cci.20210320"
    description = "Header-only library of IEEE-754 half-precision (16-bit) floating-point conversion routines (incl. ARM alternative format and PSIMD helpers)"
    license = "MIT"
    homepage = "https://github.com/Maratyszcza/FP16"
    url = "https://github.com/Maratyszcza/FP16"

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
        copy(self, pattern="fp16.h", src=include_src, dst=include_dst)
        copy(self, pattern="*.h", src=os.path.join(include_src, "fp16"),
             dst=os.path.join(include_dst, "fp16"))
        copy(self, pattern="*.py", src=os.path.join(include_src, "fp16"),
             dst=os.path.join(include_dst, "fp16"))

    def package_info(self):
        # Header-only: no link libraries, no bin/lib dirs.
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        # Upstream CMakeLists.txt defines an INTERFACE target named `fp16`.
        self.cpp_info.set_property("cmake_file_name", "fp16")
        self.cpp_info.set_property("cmake_target_name", "fp16::fp16")