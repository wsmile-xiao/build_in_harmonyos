#!/usr/bin/env python3
"""Conan recipe — lightmapper 2.8 (header-only single-file library).

lightmapper.h is a C/C++ single-header lightmap baking library: the consumer
uses its existing OpenGL renderer to bounce light.  This package ships only
the header; the GL symbols it references are provided by the consumer's own
OpenGL implementation, so the package itself builds nothing (header-only).

Upstream has no release tags; the pinned source is the upstream master HEAD
commit 4fd3bf4e2c07263f85d5d875ebdef061bc512dd4 (2022-01-03), fetched from the
official GitHub archive URL.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class LightmapperConan(ConanFile):
    name = "lightmapper"
    version = "2.8"
    description = "A C/C++ single-file library for drop-in lightmap baking (uses existing OpenGL renderer)"
    license = "public-domain"
    homepage = "https://github.com/ands/lightmapper"
    url = ""  # CI fills this

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # header-only: no compile step; patches: {} so this is a no-op
        apply_conandata_patches(self)

    def package(self):
        copy(self, "*.h", src=self.source_folder, dst=os.path.join(self.package_folder, "include"), keep_path=False)

    def package_id(self):
        self.info.clear()  # header-only -> single package_id

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]