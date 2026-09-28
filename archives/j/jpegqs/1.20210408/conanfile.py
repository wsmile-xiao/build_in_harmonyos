#!/usr/bin/env python3
"""Conan recipe - jpegqs 1.20210408 (JPEG quantization smoothing: library + CLI).

Upstream: Ilya Kurdyukov, jpeg-quantsmooth. The source tarball is the
upstream official release-tag archive (GitHub tag 1.20210408), measured
byte-identical to the Debian pool pristine ".orig" (same sha256, 65410 bytes,
cmp RC=0), i.e. unmodified upstream sources with no Debian delta.

Build system: bare Makefile - no configure script, no install rule, no
upstream test suite. package() therefore copies the artifacts by hand (E174:
OHOS ships no coreutils install(1)) while still packaging through
`conan create` (R16: no manual packaging).

Two artifacts are produced:
  * libjpegqs.a + libjpegqs.h  (smoothing API for consumers)
  * jpegqs                     (command line tool, links libjpeg)

Build flags chosen explicitly (rationale in notes.md):
  SIMD=none  -> -DNO_SIMD, portable scalar path. Upstream defaults to
                `SIMD := native` i.e. -march=native, which bakes the build
                host ISA into the binary and is not reproducible for CI.
  MTOPTS=    -> drops -fopenmp. quantsmooth.h includes <omp.h> and wraps every
                OpenMP loop in #ifdef _OPENMP with an
                `#define omp_get_thread_num() 0` fallback, so the scalar build
                stays correct and needs no OpenMP runtime at link time.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class JpegqsConan(ConanFile):
    name = "jpegqs"
    version = "1.20210408"
    description = ("JPEG artifacts removal by recovering DCT coefficient "
                   "precision from the quantization table (library + CLI)")
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/ilyakurdyukov/jpeg-quantsmooth"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libjpegqs.c:28 includes "jpeglib.h" for the public JPEG types and the
        # CLI transcodes through the IJG transcode API, so libjpeg is a hard
        # build and link requirement (exact reference, no wildcard).
        self.requires("libjpeg/10")

    def validate(self):
        # R32: the os check must accept OHOS as well as Linux.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "jpegqs supports Linux/OHOS only, got os=%s" % self.settings.os)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    @staticmethod
    def _abs(dep, paths):
        out = []
        for p in paths or []:
            out.append(p if os.path.isabs(p) else os.path.join(dep.package_folder, p))
        return out

    def build(self):
        apply_conandata_patches(self)
        # R33: compiler/ARCHIVER come from Conan conf, never from bare shell
        # variables (they are empty on CI workers).
        execs = self.conf.get("tools.build:compiler_executables",
                              check_type=dict, default={})
        cc = execs.get("c") or "clang"
        ar = execs.get("ar") or "llvm-ar"
        jpeg = self.dependencies["libjpeg"]
        incs = " ".join(["-I" + p for p in self._abs(jpeg, jpeg.cpp_info.includedirs)])
        libd = " ".join(["-L" + p for p in self._abs(jpeg, jpeg.cpp_info.libdirs)])
        # The Makefile takes the libjpeg flags in the JPEGLIB variable and
        # filters its -I tokens into CFLAGS_APP, so one variable covers both
        # the object compilation and the final link.
        jpeglib = incs + " " + libd + " -ljpeg"
        cmd = ('make CC=%s AR=%s SIMD=none MTOPTS= JPEGLIB="%s" -j1 app lib'
               % (cc, ar, jpeglib))
        self.run(cmd, cwd=self.source_folder)

    def package(self):
        pkg = self.package_folder
        src = self.source_folder
        copy(self, "jpegqs", src, os.path.join(pkg, "bin"))
        copy(self, "libjpegqs.a", src, os.path.join(pkg, "lib"))
        copy(self, "libjpegqs.h", src, os.path.join(pkg, "include"))
        copy(self, "LICENSE", src, os.path.join(pkg, "licenses"))
        copy(self, "jpegqs.1", src, os.path.join(pkg, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = ["jpegqs"]
        self.cpp_info.system_libs = ["m"]
