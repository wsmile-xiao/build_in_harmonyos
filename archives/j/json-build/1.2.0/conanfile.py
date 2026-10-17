#!/usr/bin/env python3
"""Conan recipe for json-build 1.2.0 — a zero-allocation JSON serializer
written in ANSI C (C89). Single-header, header-only library.

Variant A (header-only): only the header is packaged; no build step.
"""
from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.cmake import cmake_layout


class JsonBuildConan(ConanFile):
    name = "json-build"
    version = "1.2.0"
    description = "Zero-allocation JSON serializer written in ANSI C (header-only)"
    license = "MIT"
    homepage = "https://github.com/lcsmuller/json-build"
    url = ""  # CI fills this

    package_type = "header-library"

    settings = "os", "arch", "compiler", "build_type"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        cmake_layout(self, src_folder=".")

    def build(self):
        # Header-only library: nothing to compile. Apply any conandata
        # patches only (currently none), keeping the recipe self-contained.
        apply_conandata_patches(self)

    def package(self):
        copy(self, "*.h", src=self.source_folder, dst=self.package_folder)
        copy(self, "LICENSE*", src=self.source_folder, dst="licenses", keep_path=False)

    def package_id(self):
        self.info.clear()  # No build dependency on os/compiler -> single package_id

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["."]
