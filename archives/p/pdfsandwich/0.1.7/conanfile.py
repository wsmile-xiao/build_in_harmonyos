#!/usr/bin/env python3
"""Conan recipe — pdfsandwich 0.1.7

pdfsandwich is a command-line tool that generates "sandwich" OCR PDF files.
It is written in OCaml and compiled to a native binary.

Build-time dependency: OCaml compiler (tool_requires).
The OCaml conan package exposes its bin/ via env_info.PATH, so ocamlopt
is automatically available during build. However, ocamlc -where returns
a stale build-time path (conan cache relocation), so we set OCAMLLIB
explicitly by deriving the correct library directory from the ocamlc
binary location in PATH.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PdfsandwichConan(ConanFile):
    name = "pdfsandwich"
    version = "0.1.7"
    description = "Command-line tool for generating sandwich OCR PDF files"
    license = "MIT"
    homepage = "https://sourceforge.net/projects/pdfsandwich/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # OCaml is a build-time tool dependency (compiler), not a runtime dependency
        self.tool_requires("ocaml/4.14.1.1.4")

    def layout(self):
        self.folders.build = "."
        self.folders.source = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Bypass configure script: it checks `test -d $(ocamlc -where)` which
        # fails because ocamlc -where returns a stale path after conan cache relocation.
        # Instead, write makefile.installprefix directly.
        prefix = os.path.join(self.package_folder, "res")
        with open("makefile.installprefix", "w") as f:
            f.write(f"PREFIX={prefix}\n")
        # OCaml's ocamlc -where returns a stale path after conan cache relocation.
        # Derive OCAMLLIB from the ocamlc binary location in PATH (set by tool_requires).
        self.run(
            'OCAMLLIB="$(d=$(dirname "$(realpath "$(which ocamlc)")"); '
            'echo "$(dirname "$d")/lib/ocaml")" make -j1',
            env="conanbuild"
        )

    def package(self):
        dest = os.path.join(self.build_folder, "dest_install")
        self.run(
            'OCAMLLIB="$(d=$(dirname "$(realpath "$(which ocamlc)")"); '
            'echo "$(dirname "$d")/lib/ocaml")" '
            f'make install DESTDIR="{dest}"',
            env="conanbuild"
        )
        # Copy from dest/<prefix>/ to package_folder
        prefix = os.path.join(self.package_folder, "res")
        src_base = os.path.join(dest, prefix.lstrip("/"))
        if not os.path.isdir(src_base):
            src_base = dest
        copy(self, "*", src_base, self.package_folder)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
