#!/usr/bin/env python3
"""Conan recipe for jsonnet — pure Makefile project (no configure).

jsonnet uses a Makefile-based build system. No configure step needed.
The patch fixes HMDFS symlink compatibility (ln -sf → rm -f && ln -s).
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class JsonnetConan(ConanFile):
    name = "jsonnet"
    version = "v0.20.0"
    description = "Jsonnet is a data templating language for app and tool developers"
    license = "Apache-2.0"
    homepage = "https://jsonnet.org/"
    url = "https://github.com/google/jsonnet"

    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler_c(self):
        # R33: take the compiler from the Conan profile, never from shell env.
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return executables.get("c") or "clang"

    def _compiler_cxx(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return executables.get("cpp") or "clang++"

    def build(self):
        apply_conandata_patches(self)
        cc = self._compiler_c()
        cxx = self._compiler_cxx()
        # jsonnet uses pure Makefile, no configure step
        # Build executables and shared libraries
        self.run(
            f'make CC="{cc}" CXX="{cxx}" -j1 jsonnet jsonnetfmt libs',
            cwd=self.source_folder,
        )

    def package(self):
        # Install using Makefile's install target
        # PREFIX="" so files go directly to DESTDIR/{bin,lib,include}
        self.run(
            f'make DESTDIR="{self.package_folder}" PREFIX="" install',
            cwd=self.source_folder,
        )

    def package_info(self):
        self.cpp_info.libs = ["jsonnet"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
