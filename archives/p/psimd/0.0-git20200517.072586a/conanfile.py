#!/usr/bin/env python3
"""Conan recipe — psimd 0.0-git20200517.072586a (header-only, nothing to compile).

PSIMD is a single-header (psimd.h) portable 128-bit SIMD wrapper: NEON on
ARM/aarch64, SSE/AVX on x86, SIMD128 on WAsm. Upstream builds an INTERFACE
(header-only) CMake target and installs only include/psimd.h.

The recipe never invokes upstream CMake on purpose: upstream CMakeLists.txt
still declares CMAKE_MINIMUM_REQUIRED(VERSION 2.8.12) (rejected by CMake 4.x,
E103/E321) and registers no tests. Copying the header (E257 header-only
pattern) makes the package independent of that legacy build file.

Upstream snapshot: 072586a71b55b7f8c584153d223e95687148a900 (2020-05-17,
"Fix psimd_qfma_f32 for FMA-enabled x86 processors"; repo archived read-only
2024-05-27).

Reference: archives/f/fp16/cci.20210320/ (header-only CMake pattern).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches


class PsimdConan(ConanFile):
    name = "psimd"
    version = "0.0-git20200517.072586a"
    description = "Portable 128-bit SIMD intrinsics (single-header: NEON/SSE/AVX/WAsm SIMD128)"
    license = "MIT"
    homepage = "https://github.com/Maratyszcza/psimd"
    url = "https://github.com/Maratyszcza/psimd"

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

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
        copy(self, pattern="psimd.h", src=include_src, dst=include_dst)
        copy(self, pattern="LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Header-only: no link libraries, no bin/lib dirs.
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        # Upstream CMakeLists.txt defines an INTERFACE target named `psimd`.
        self.cpp_info.set_property("cmake_file_name", "psimd")
        self.cpp_info.set_property("cmake_target_name", "psimd::psimd")
