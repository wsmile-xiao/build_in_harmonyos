#!/usr/bin/env python3
"""Conan recipe — GNU Octave 8.3.0 for HarmonyOS (aarch64).

Octave is a high-level numerical computing language. This recipe documents
the build approach for HarmonyOS where no native Fortran compiler exists.

Key build challenges on HarmonyOS:
  - No native Fortran compiler; f2c + custom gfortran wrapper used instead
  - f2c integer type must be patched to int (4 bytes) to match Octave's F77_INT
  - BLAS/LAPACK .f90 files cannot be compiled by f2c; C stubs used instead
  - dgebal.f uses Fortran 90 syntax (EXIT/CYCLE/END DO); patched to F77
  - DLAMCH machine constants return wrong values; C replacement (mach-params.c)
  - OpenMP not available; omp_stub.c provides single-threaded stubs
  - Autotools regeneration loops patched to no-op; manual linking required

Dependencies (all built from source, not Conan packages):
  - f2c (Fortran-to-C translator)
  - BLAS 3.12.0 (reference, built with f2c)
  - LAPACK 3.12.1 (reference, built with f2c)
  - PCRE 8.45 (with UTF/Unicode support)
  - FreeType, libpng, zlib
  - libohpc_compat (reallocarray compatibility)
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class OctaveConan(ConanFile):
    name = "octave"
    version = "8.3.0"
    description = "GNU Octave: high-level numerical computing language and environment"
    license = "GPL-3.0-or-later"
    homepage = "https://www.octave.org"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Dependencies are built from source, not Conan packages.
        # In a full CI pipeline, these would be:
        # self.requires("blas/3.12.0")
        # self.requires("lapack/3.12.1")
        # self.requires("pcre/8.45")
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: Terminal tools must be statically linked
        tc.extra_ldflags.append("-static")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["octinterp", "octave", "gnu"]
        self.cpp_info.includedirs = ["include/octave-8.3.0"]
