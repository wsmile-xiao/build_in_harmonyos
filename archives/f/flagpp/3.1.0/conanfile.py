#!/usr/bin/env python3
"""Conan recipe — flagpp 3.1.0 (header-only C++23 flags library).

flagpp (https://github.com/Curve/flagpp) is a header-only C++23 library
providing type-safe bitwise operations for scoped enums. No compiled
artifacts are produced; the package redistributes include/ only.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class FlagppConan(ConanFile):
    name = "flagpp"
    version = "3.1.0"
    description = "Header-only C++23 library for type-safe scoped-enum bitwise operations"
    license = "MIT"
    homepage = "https://github.com/Curve/flagpp"
    url = ""  # CI fills this

    package_type = "header-library"

    # Header-only: no compiled artifacts
    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Header-only: nothing to compile (R34: no fake build logs).
        # Only patches are applied if any exist.
        apply_conandata_patches(self)

    def package(self):
        include_src = os.path.join(self.source_folder, "include", "flagpp")
        include_dst = os.path.join(self.package_folder, "include", "flagpp")
        print(f"[DEBUG] source_folder={self.source_folder}")
        print(f"[DEBUG] package_folder={self.package_folder}")
        print(f"[DEBUG] include_src={include_src} exists={os.path.isdir(include_src)}")
        copy(self, "*.hpp", src=include_src, dst=include_dst)
        copy(self, "*.inl", src=include_src, dst=include_dst)
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()          # header-only: single package_id

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
