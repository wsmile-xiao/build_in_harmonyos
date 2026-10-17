#!/usr/bin/env python3
"""Conan recipe — cbflib 0.9.7 (CBF/imgCIF Crystallographic Binary File library).

Upstream: https://github.com/yayahjb/cbflib (tag CBFlib-0.9.7)
Build system: plain Makefile generated upstream from m4/Makefile.m4 (shipped
pre-generated; no configure step).

Upstream build facts driving this recipe:
  - `include/cbf_hdf5.h` unconditionally `#include <hdf5.h>`: HDF5 is a hard
    dependency of libcbf (cbf_hdf5.c is part of the core library).
  - `HDF5_PREFIX=<external prefix>` switches the Makefile to a system HDF5
    (CBFLIB_DONT_USE_LOCAL_HDF5) instead of downloading/regex-building
    hdf5-1.12.0, pcre-8.38, tiff and PyCifRW snapshots from sourceforge.
  - `CBFLIB_DONT_USE_LZ4/BSHUF=yes` skips the optional bundled HDF5 filter
    plugins (upstream-supported configuration; core CBF compressions are not
    affected).
  - `NOFORTRAN=1` disables libfcb (no Fortran compiler in the OHOS toolchain).
  - regex support uses pcreposix (CBF_REGEXLIB_REGEX default) from pcre/8.45.
  - `CBFLIB_DONT_USE_TIFF=yes` (added by our patch, following the existing
    CBFLIB_DONT_USE_* convention) removes the tiff2cbf tool from `all`/`extra`;
    no tiff recipe is published for OHOS.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import GnuToolchain
from conan.tools.layout import basic_layout


class CbflibConan(ConanFile):
    name = "cbflib"
    version = "0.9.7"
    description = "CBF/imgCIF Crystallographic Binary File library (libcbf, libimg) with CIF<->CBF conversion tools"
    license = "GPL-2.0-or-later OR LGPL-2.1-or-later"
    homepage = "https://github.com/yayahjb/cbflib"
    url = "https://github.com/yayahjb/cbflib"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libcbf core includes hdf5 headers and links -lhdf5 (cbf_hdf5.c)
        self.requires("hdf5/1.14.6")
        # regex support (default CBF_REGEXLIB_REGEX) links pcreposix from pcre 8.x
        self.requires("pcre/8.45")
        # zlib and libaec come transitively via hdf5

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"cbflib is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Generates conanbuild env (injects the profile buildenv PATH so that
        # ar/ranlib resolve) for the raw make invocation in build().
        tc = GnuToolchain(self)
        tc.generate()

    def _conf_tool(self, key, fallback):
        # Conan 2.29: point-subkey access on tools.build:compiler_executables
        # raises ConanException — fetch the dict first, then index (R33).
        comp_execs = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return comp_execs.get(key) or fallback

    def build(self):
        apply_conandata_patches(self)

        src = self.source_folder
        # The Makefile has a `Makefile: m4/Makefile.m4` regeneration rule.
        # Both files arrive patched, but their mtimes could make GNU make
        # auto-regenerate the Makefile with m4 (absent on build machines).
        # Pin both to a fixed historical timestamp (boolstuff precedent).
        pin = 1600000000
        for rel in ("Makefile", os.path.join("m4", "Makefile.m4")):
            os.utime(os.path.join(src, rel), (pin, pin))

        cc = self._conf_tool("c", "clang")
        cxx = self._conf_tool("cpp", "clang++")
        ar = self._conf_tool("ar", "ar")
        ranlib = self._conf_tool("ranlib", "ranlib")

        # Collect include/lib dirs of every visible dependency (hdf5, pcre,
        # zlib, libaec, ...) for the explicit make variable wiring.
        inc_dirs = []
        lib_dirs = []
        for dep in self.dependencies.values():
            inc_dirs.extend(dep.cpp_info.includedirs)
            lib_dirs.extend(dep.cpp_info.libdirs)
        includes = " ".join(f"-I{d}" for d in inc_dirs)
        ldflags = " ".join(f"-L{d}" for d in lib_dirs)

        hdf5_dep = self.dependencies["hdf5"]
        pcre_dep = self.dependencies["pcre"]
        hdf5_prefix = os.path.dirname(hdf5_dep.cpp_info.includedirs[0])
        pcre_prefix = os.path.dirname(pcre_dep.cpp_info.includedirs[0])
        pcre_lib = pcre_dep.cpp_info.libdirs[0]

        opt = "-O3" if self.settings.build_type == "Release" else "-O0 -g"
        cflags = f"{opt} -D_USE_XOPEN_EXTENDED -fno-strict-aliasing -DH5_USE_110_API"
        regex_libs = f"-L{pcre_lib} -lpcreposix -lpcre"

        make_vars = (
            f'CC="{cc}" AR="{ar}" RANLIB="{ranlib}" '
            f'CFLAGS="{cflags}" LDFLAGS="{ldflags}" '
            f'INCLUDES="-Iinclude -Isrc {includes}" '
            f'HDF5_PREFIX="{hdf5_prefix}" REGEX_PREFIX="{pcre_prefix}" '
            f'REGEX_LIBS="{regex_libs}" '
            "NOFORTRAN=1 "
            "CBFLIB_DONT_USE_LZ4=yes CBFLIB_DONT_USE_BSHUF=yes "
            "CBFLIB_DONT_USE_PY2CIFRW=yes CBFLIB_DONT_USE_PY3CIFRW=yes "
            "CBFLIB_DONT_USE_TIFF=yes"
        )
        # `C++` cannot be set as a make command-line variable (the parser reads
        # `C++=x` as an append to variable `C+`); the m4 patch changed the
        # default-section assignment to `?=`, so the environment wins.
        cmd = (
            f'env "C++={cxx}" make -j1 all {make_vars} && '
            f'env "C++={cxx}" make -j1 '
            f'"{os.path.join(src, "solib", "libcbf.so")}" '
            f'"{os.path.join(src, "solib", "libimg.so")}" '
            f'SOLDFLAGS="-shared" {make_vars}'
        ) if self.options.shared else (
            f'env "C++={cxx}" make -j1 all {make_vars}'
        )
        self.run(cmd, cwd=src)

    def package(self):
        src = self.source_folder
        # headers
        copy(self, "*.h", os.path.join(src, "include"),
             os.path.join(self.package_folder, "include"))
        # libraries: shared build keeps only the .so pair, static keeps .a pair
        if self.options.shared:
            copy(self, "*.so", os.path.join(src, "solib"),
                 os.path.join(self.package_folder, "lib"))
        else:
            copy(self, "*.a", os.path.join(src, "lib"),
                 os.path.join(self.package_folder, "lib"))
        # CLI tools built by upstream `all`
        copy(self, "*",
             os.path.join(src, "bin"),
             os.path.join(self.package_folder, "bin"),
             excludes=("*.tmp", "*.class"))

    def package_info(self):
        self.cpp_info.libs = ["cbf", "img"]
        self.cpp_info.system_libs = ["m", "dl"]
        self.cpp_info.bindirs = ["bin"]
        # cbf.h includes hdf5.h; static libcbf.a references pcreposix and H5*
        # symbols — consumers must inherit hdf5/pcre include dirs and libs.
        self.cpp_info.requires = ["hdf5::hdf5", "pcre::pcre"]
