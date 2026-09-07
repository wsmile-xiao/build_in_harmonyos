#!/usr/bin/env python3
"""Conan recipe — primer3 2.6.1 (upstream Makefile build, no configure step).

Upstream: https://github.com/primer3-org/primer3
Primer3 is a PCR primer design toolchain: 7 static libraries
(libprimer3/libdpal/libthal/libthalpara/liboligotm/libamplicontm/libmasker)
plus 7 command line tools (primer3_core/ntdpal/ntthal/oligotm/
amplicon3_core/long_seq_tm_test/primer3_masker).

Build notes (verified on the full official tarball, E350-class pitfall):
  * The tarball has NO top-level configure (not autotools); the Makefile
    lives in the src/ subdirectory of the extracted primer3-2.6.1/ tree.
  * `make all` in src/ builds EXES + static LIBRARIES; the `install`
    target only installs EXES, so package() copies artifacts manually.
  * CC/CXX/AR/RANLIB are plain Makefile variables -> zero-patch cross
    build by variable injection (no x86-specific flags in the Makefile).
  * libprimer3.cc is C++11 (the only C++ source); everything else is C,
    so the test_package executable must link with the C++ linker.

This recipe is Makefile-based (raw make, no configure), per
templates/conanfile-makefile.py.tmpl. Rules honored:
  R9  : fixed small parallelism (-j2), never -j$(nproc)
  R26 : primer3 ships static libs only via the default `all` target
  R33 : compiler paths come from Conan conf, never from shell env vars
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class Primer3Conan(ConanFile):
    name = "primer3"
    version = "2.6.1"
    description = (
        "Primer3: PCR primer design tool (libprimer3 core library plus "
        "primer3_core, ntthal, oligotm and other command line tools)"
    )
    license = "GPL-2.0"  # verified against LICENSE in the source tarball
    homepage = "https://primer3.org"
    url = "https://github.com/primer3-org/primer3"

    # Library + CLI mix: cpp_info.libs is the primary interface; the 7
    # executables are additionally packaged into bin/ (see package()).
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # primer3 is self-contained: no third-party dependencies.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: take compiler paths from Conan conf (profile sets
        # tools.build:compiler_executables as a dict) — never rely on bare
        # ${CC}/${CXX} shell variables. AR/RANLIB come from the OHOS
        # toolchain dir which is on the buildenv PATH.
        # NOTE: on conan 2.29.1 reading subkeys of compiler_executables
        # with check_type=str raises ("does not exist in configuration
        # list"); read the whole dict and index it instead.
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        cxx = compilers.get("cpp", "clang++")
        ar = "llvm-ar"
        ranlib = "llvm-ranlib"

        # The Makefile is in src/ of the full tarball tree (not the
        # promoted-layout .work copy). `all` = 7 EXES + 7 static libs.
        # Upstream default CFLAGS (-g -Wall -O2, -std=c++11 for C++) are
        # kept as-is; no x86-specific flags upstream.
        # NOTE: with basic_layout the build cwd is build-release/, so the
        # Makefile directory must be addressed by its absolute path.
        src_dir = os.path.join(self.source_folder, "src")
        self.run(
            f'make -C "{src_dir}" CC={cc} CXX={cxx} AR={ar} RANLIB={ranlib} -j2'
        )

    def package(self):
        src = os.path.join(self.source_folder, "src")
        pkg = self.package_folder

        # 7 executables -> bin/ (upstream `install` target only copies
        # EXES anyway; we replicate plus the libraries/headers below).
        for exe in ("primer3_core", "ntdpal", "ntthal", "oligotm",
                    "amplicon3_core", "long_seq_tm_test", "primer3_masker"):
            copy(self, exe, src, os.path.join(pkg, "bin"))

        # 7 static libraries -> lib/
        copy(self, "*.a", src, os.path.join(pkg, "lib"))

        # Public headers (flat layout in src/) -> include/
        copy(self, "*.h", src, os.path.join(pkg, "include"))

    def package_info(self):
        # Link order matters for static linking: libprimer3 references
        # symbols from dpal/thal/thalpara/oligotm (and transitively
        # amplicontm/masker for the full CLI set).
        self.cpp_info.libs = [
            "primer3",
            "dpal",
            "thal",
            "thalpara",
            "oligotm",
            "amplicontm",
            "masker",
        ]
        # Tool-class packaging (code-style.md §4): the 7 packaged CLI
        # executables live in bin/, so expose bindirs explicitly.
        self.cpp_info.bindirs = ["bin"]
