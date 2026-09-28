#!/usr/bin/env python3
"""Conan recipe — buddy_alloc 1.3.2 (single-header C99 buddy memory allocator).

buddy_alloc is a binary buddy memory allocator published as ONE C99 header
(buddy_alloc.h, BUDDY_ALLOC_IMPLEMENTATION pattern). No compiled artifacts:
consumers #define BUDDY_ALLOC_IMPLEMENTATION in exactly one translation unit
and include the header. Recipe packages the header + MIT license.
"""
from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout
import os


class BuddyAllocConan(ConanFile):
    name = "buddy_alloc"
    version = "1.3.2"
    description = ("buddy_alloc — binary buddy memory allocator, single-header "
                   "C99 library (BUDDY_ALLOC_IMPLEMENTATION pattern)")
    license = "MIT"
    homepage = "https://github.com/spaskalev/buddy_alloc"
    url = "https://github.com/spaskalev/buddy_alloc"  # CI fills this

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # header-only, zero runtime dependencies
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # header-only: no compilation step (R34 — no fake build logs);
        # only source patches are applied (empty for this recipe).
        apply_conandata_patches(self)

    def package(self):
        # header-only: install the single public header under include/ and the
        # MIT license under licenses/ (absolute dst — Conan 2 copy() resolves
        # relative dst against cwd, which is not stable inside the cache flow).
        copy(self, "*.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "LICENSE.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()  # header-only: single package_id, no ABI dimension

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []