#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conan recipe for kernsmooth 2.23-26 on native HarmonyOS aarch64.

kernsmooth is an R package (functions for kernel smoothing supporting
Wand & Jones (1995) "Kernel Smoothing") shipped as 11 Fortran 77 source
files plus one C file. On HarmonyOS we avoid the R toolchain entirely
(r-base is NOT published to the ohpcd Conan remote — see notes.md) and
instead compile the Fortran 77 numerical core into a standalone static
library libkernsmooth.a, exposing the same symbols that would otherwise
be registered by src/init.c:

    blkest_  cp_  linbin_  lbtwod_  locpol_  rlbin_  sdiag_  sstdg_

Key points:
- tool_requires("flang-ohos/20.1.0") provides the Fortran compiler flang
  (path: <package_folder>/bin/flang), target aarch64-unknown-linux-ohos.
- requires("openblas/0.3.33") provides the BLAS symbols dscal_/daxpy_/ddot_
  used by the bundled LINPACK routines dgefa/dgesl/dgedi.
- All 11 .f files are compiled with -fPIC -O2 (LINPACK d* need BLAS but not
  LAPACK). init.c is NOT compiled (depends on R headers absent locally).
- LINPACK dqrdc/dqrsl (needed by blkest.f and cp.f) are added by patches
  0001/0002 from netlib.org (public domain) into src/ and compiled too.
- Layout: lib/libkernsmooth.a + include/kernsmooth.h (header written by the
  OHOS port since upstream ships Fortran-only entry points).
- See test_package/test_kernsmooth.c for substantive numerical tests
  (R34) — calls linbin_/rlbin_/locpol_ and verifies results.
- Notes: F77 name mangling -> lowercase + trailing underscore; args passed
  by reference (pointers). Documented in include/kernsmooth.h.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, copy


class KernsmoothConan(ConanFile):
    name = "kernsmooth"
    version = "2.23-26"
    description = "Functions for kernel smoothing supporting Wand & Jones (1995)"
    license = "Unlimited"          # upstream LICENSE.note: unlimited use/distribution
    homepage = "https://cran.r-project.org/package=KernSmooth"
    url = "https://cran.r-project.org/src/contrib/Archive/KernSmooth/KernSmooth_2.23-26.tar.gz"
    topics = ("r", "r-package", "smoothing", "kernsmooth", "wand-jones", "ohos")

    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml", "patches/*"

    def requirements(self):
        """openblas: BLAS symbols used by LINPACK dgefa/dgesl/dgedi."""
        self.requires("openblas/0.3.33")

    def build_requirements(self):
        """flang: Fortran compiler (no gfortran on HarmonyOS). r-base is NOT
        published to ohpcd, so the R CMD INSTALL route is impossible."""
        self.tool_requires("flang-ohos/20.1.0")

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _flang(self):
        """Return (folder, flang_path) from Conan tool_requires."""
        flang = self.dependencies.build.get("flang-ohos")
        if not flang:
            raise ConanException("flang-ohos tool_requires not found")
        folder = flang.package_folder
        p = os.path.join(folder, "bin", "flang")
        if not os.path.isfile(p):
            raise ConanException("flang compiler not found: %s" % p)
        return folder, p

    def build(self):
        apply_conandata_patches(self)
        _, flang = self._flang()

        src = os.path.join(self.source_folder, "src")
        if not os.path.isdir(src):
            raise ConanException("src/ directory missing in source folder")
        build = self.build_folder
        os.makedirs(build, exist_ok=True)

        order = [
            "sdiag.f", "sstdiag.f", "rlbin.f", "linbin.f", "linbin2D.f",
            "locpoly.f", "blkest.f", "cp.f",
            "dgedi.f", "dgefa.f", "dgesl.f",
            "dqrdc.f", "dqrsl.f",
        ]
        objs = []
        for f in order:
            p = os.path.join(src, f)
            if not os.path.isfile(p):
                raise ConanException("source missing: %s" % p)
            o = os.path.join(build, f[:-2] + ".o")
            self.run("%s -c -fPIC -O2 -o %s %s" % (flang, o, p), quiet=True)
            objs.append(o)
            self.output.info("compiled %s" % f)

        libpath = os.path.join(build, "libkernsmooth.a")
        # ar/ranlib come from the tools.build:compiler_executables conf dict (R33)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        ar = compilers.get("ar", "llvm-ar")
        self.run("%s rcs %s %s" % (ar, libpath, " ".join(objs)), quiet=True)

        # header written by the OHOS port (upstream ships Fortran-only entry
        # points). It lives alongside the patches in the exported sources;
        # self.recipe_folder is NOT available when building from the cache.
        include_out = os.path.join(build, "include")
        os.makedirs(include_out, exist_ok=True)
        copy(self, "kernsmooth.h", os.path.join(self.export_sources_folder, "patches"),
             include_out)
        self.output.info("built libkernsmooth.a (%d objects)" % len(objs))

    def package(self):
        copy(self, "libkernsmooth.a", self.build_folder,
             os.path.join(self.package_folder, "lib"))
        copy(self, "kernsmooth.h", os.path.join(self.export_sources_folder, "patches"),
             os.path.join(self.package_folder, "include"))
        copy(self, "LICENCE.note", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["kernsmooth"]
        self.cpp_info.set_property("pkg_config_name", "kernsmooth")
        # consumers need libm when linking the static lib
        self.cpp_info.system_libs = ["m"]
