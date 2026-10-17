#!/usr/bin/env python3
"""Conan recipe — arena 20260923 (header-only C library).

tsoding/arena: stb-style single-file arena allocator (arena.h).
Header-only: consumer defines ARENA_IMPLEMENTATION before including arena.h.
"""
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class ArenaConan(ConanFile):
    name = "arena"
    version = "20260923"
    description = "Arena Allocator — single-file C region-based memory allocator (tsoding/arena)"
    license = "MIT"
    homepage = "https://github.com/tsoding/arena"
    url = ""  # CI fills this
    topics = ("arena", "allocator", "memory", "region", "header-only", "c")

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # Header-only library: nothing to compile (R34: no fake build logs).
        # Patches (if any) are applied in source(); consumers get the header
        # unchanged and define ARENA_IMPLEMENTATION at include time.
        pass

    def package(self):
        copy(
            self,
            "arena.h",
            src=self.source_folder,
            dst=self.package_folder,
        )
        copy(
            self,
            "LICENSE*",
            src=self.source_folder,
            dst=self.package_folder,
            keep_path=False,
        )

    def package_id(self):
        self.info.clear()          # header-only → single package_id

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["."]
