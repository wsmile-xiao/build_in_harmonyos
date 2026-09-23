#!/usr/bin/env python3
"""Conan recipe — picojson 1.3.0 (header-only, variant A).

picojson is a header-only C++ JSON parser. Upstream distributes a single
picojson.h plus its picotest-based test suite (test.cc). There is no
configure script; the upstream Makefile only builds the test binaries and
installs the header. Per the header-only template (v12.21) we skip build()
entirely and package the header with Conan's copy().
"""
from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class PicojsonConan(ConanFile):
    name = "picojson"
    version = "1.3.0"
    description = "picojson 1.3.0 — header-only JSON parser for C++"
    license = "MIT"
    homepage = "https://github.com/kazuho/picojson"
    url = "https://github.com/kazuho/picojson"

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Header-only: no compilation. No-op body (R34 — no fake build logs).
        apply_conandata_patches(self)

    def package(self):
        import os
        # Absolute dst paths are required — relative "include" resolves against
        # the process CWD, which is not the package folder (repo convention).
        copy(self, "picojson.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()  # header-only -> single package_id

    def package_info(self):
        # Header-only: no compiled libraries (code_style §4 — cpp_info.libs N/A)
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []