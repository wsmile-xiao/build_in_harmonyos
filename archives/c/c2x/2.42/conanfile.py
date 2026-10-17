#!/usr/bin/env python3
"""Conan recipe for c2x 2.42 — crystal structure visualisation/conversion tool.

c2x converts between the file formats of major solid-state physics codes
(CASTEP, VASP, Quantum ESPRESSO, ABINIT, ...), with band/density analysis.
Single C binary built from a plain Makefile (no configure).

This build uses upstream's documented no-SPGLIB configuration
(`make CC=... DEFS= CPPFLAGS=-I. LDFLAGS= LIBS=`): spglib is not yet
published to the ohpcd artifact registry, and upstream explicitly supports
building without it. Feature impact is documented in notes.md; when spglib
is adapted and released, a follow-up version can enable -DSPGLIB.

License: GPL-3.0 (LICENCE file in the tarball). The Makefile provides no
install target; package() copies the produced binary.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class C2xConan(ConanFile):
    name = "c2x"
    version = "2.42"
    description = "Converts and analyses crystal structure files between CASTEP, VASP, QE, ABINIT and other formats"
    license = "GPL-3.0-or-later"
    homepage = "https://c2x.org.uk/"
    url = ""

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        self.folders.build = "."
        self.folders.generators = "."

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"OS {self.settings.os} not supported, requires Linux or OHOS"
            )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: the Makefile hard-assigns CC=gcc, CFLAGS and the SPGLIB flags,
        # so everything is overridden on the make command line (command-line
        # variables beat Makefile assignments). Empty DEFS/LDFLAGS/LIBS select
        # upstream's supported no-SPGLIB configuration; -lm comes from the
        # link rule itself.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")
        self.run(f'make -j1 CC="{cc}" DEFS= CPPFLAGS=-I. LDFLAGS= LIBS=')

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        shutil.copy2(
            os.path.join(self.source_folder, "c2x"),
            os.path.join(bin_dir, "c2x"),
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
