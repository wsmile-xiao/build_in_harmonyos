#!/usr/bin/env python3
"""Conan recipe for avy — GNU Emacs Lisp package for jumping to tree-based visual selections.

avy is a pure Emacs Lisp package. No C/C++ compilation needed.
Build() copies .el files to the package directory.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AvyConan(ConanFile):
    name = "avy"
    version = "0.5.0.1"
    description = "GNU Emacs Lisp package for jumping to tree-based visual selections"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/abo-abo/avy"
    url = ""  # CI fills this

    # Pure Elisp content package, no compiled binary
    package_type = "header-library"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # emacs is a runtime dependency loaded by Emacs at runtime,
        # not a Conan build-time dependency. It is documented in notes.md.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # avy is pure Emacs Lisp — no C/C++ compilation.
        # The Makefile only does byte-compilation via Emacs,
        # which requires Emacs runtime, not a cross-compilation toolchain.
        pass

    def package(self):
        # Copy .el files to the package lib directory (site-lisp for Emacs)
        copy(self, "*.el", self.source_folder, os.path.join(self.package_folder, "lib", "site-lisp"))
        # Copy README and LICENSE if present
        copy(self, "README*", self.source_folder, os.path.join(self.package_folder, "lib", "site-lisp"))
        copy(self, "LICENSE*", self.source_folder, os.path.join(self.package_folder, "lib", "site-lisp"))

    def package_info(self):
        # Emacs Lisp packages don't have C/C++ libraries to link against.
        # The .el files are loaded by Emacs at runtime.
        self.cpp_info.includedirs = ["lib/site-lisp"]
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
