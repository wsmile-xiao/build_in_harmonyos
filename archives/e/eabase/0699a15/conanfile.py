#!/usr/bin/env python3
"""Conan recipe — EABase 0699a15 header-only C/C++ library (Electronic Arts).

EABase supplies cross-platform base types/macros as a header-only library.
The upstream CMake target is `INTERFACE` with no compiled artifacts, so this
recipe only redistributes the public headers (variant A of the header-only
template). No build stage exists: nothing is compiled, nothing is forged.

OHOS adaptation (patches applied via conandata):
  - eaplatform.h: define EA_SYSTEM_LITTLE_ENDIAN for aarch64 Linux/OHOS;
    set EA_PLATFORM_MIN_MALLOC_ALIGNMENT=8 on OHOS ARM64 (libc probe, R8).
  - eastdarg.h: va_list_reference must be `va_list&` on aarch64 (struct ABI).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class EabaseConan(ConanFile):
    name = "eabase"
    version = "0699a15"
    description = "EABase - Electronic Arts cross-platform base types and macros (header-only)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/electronicarts/EABase"
    url = ""  # CI fills this

    package_type = "library"

    # Header-only: settings preserved for structural consistency; output
    # package_id is cleared in package_id() because there is nothing built.
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # EABase is header-only: no configure/make needed. Upstream CMake
        # INTERFACE target has nothing to compile; verification is done via
        # test_package which includes and uses the public headers.

    def package(self):
        # EABase public headers live under include/Common/EABase upstream and
        # are installed to include/EABase (mirrors upstream CMake install).
        # conan copy() dst must be an absolute path under the package folder.
        copy(self, "*", src=os.path.join(self.source_folder, "include/Common/EABase"),
             dst=os.path.join(self.package_folder, "include", "EABase"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()  # no build deps -> single package_id

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []