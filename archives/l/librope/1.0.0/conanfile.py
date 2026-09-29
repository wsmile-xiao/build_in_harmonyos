#!/usr/bin/env python3
"""Conan recipe — librope 1.0.0 (raw Makefile, no configure).

librope is a UTF-8 rope library implemented with skip lists.
The upstream Makefile only builds librope.a (no install target),
so the package step copies the static archive and header manually.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibropeConan(ConanFile):
    name = "librope"
    version = "1.0.0"
    description = "UTF-8 rope (heavyweight string) library with O(log n) insert/delete, skip-list based"
    license = "MIT"
    homepage = "https://github.com/josephg/librope"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: get the compiler from Conan conf, never from bare ${CC}
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        ar = compilers.get("ar", "llvm-ar") if compilers else "llvm-ar"
        ranlib = compilers.get("ranlib", "llvm-ranlib") if compilers else "llvm-ranlib"

        # R9: -j1 only. The Makefile builds librope.a (ar rcs).
        self.run(f"make CC={cc} AR={ar} RANLIB={ranlib} -j1", cwd=self.source_folder)

    def package(self):
        # Upstream Makefile has no install target — copy artifacts manually.
        copy(self, "rope.h", self.source_folder, os.path.join(self.package_folder, "include"))
        copy(self, "librope.a", self.source_folder, os.path.join(self.package_folder, "lib"))

    def package_info(self):
        # Archive is named librope.a → linker name is "rope" (find_library adds lib prefix)
        self.cpp_info.libs = ["rope"]