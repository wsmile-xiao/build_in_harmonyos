#!/usr/bin/env python3
"""Conan recipe for oourafft 1.0 - General Purpose FFT (Ooura).

Upstream (``petewarden/OouraFFT`` tagged ``v1.0``) ships no build system at
all: it is the original Ooura FFT package, i.e. the C sources
(``fftsg.c``/``fftsg2d.c``/``fftsg3d.c``/``fft4f2d.c``/``shrtdct.c``/
``alloc.c``) plus two sample directories.  The recipe therefore compiles the
sources into static libraries, mirroring the split used by the Debian
``libfft2d-dev`` package, and then builds and runs the upstream 1-D test
program ``sample1/testxg.c`` against the freshly built ``fft2d_fftsg``.

Upstream's own test is the authoritative check: it performs forward+inverse
round trips for cdft/rdft/ddct/ddst/dfct/dfst (6 checks) and prints the
maximum absolute error.  The recipe feeds stdin (``echo 64``) and asserts that
all six errors are below 1e-9.

There are no third-party dependencies; the 1-D transform needs libm.
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"

# (library name, single source file) - mirrors the Debian CMake split.
LIBS = (
    ("fft2d_fftsg", "fftsg.c"),
    ("fft2d_fftsg2d", "fftsg2d.c"),
    ("fft2d_fftsg3d", "fftsg3d.c"),
    ("fft2d_fft4f2d", "fft4f2d.c"),
    ("fft2d_shrtdct", "shrtdct.c"),
    ("fft2d_alloc", "alloc.c"),
)

# Only a subset can be installed together: fft4f2d.c carries its own copies of
# the private helpers (makewt/bitrv2/...) and a cdft2d with a different
# signature, so it cannot coexist with fftsg/fftsg2d in one link.  The Debian
# libfft2d-dev package installs exactly the same subset.
INSTALLED = ("fft2d_fftsg", "fft2d_fftsg2d", "fft2d_alloc")


class OourafftConan(ConanFile):
    name = "oourafft"
    version = "1.0"
    description = "General Purpose FFT (Ooura): Discrete Fourier/Cosine/Sine Transforms"
    license = "Permissive (see readme.txt)"
    homepage = "https://github.com/petewarden/OouraFFT"
    url = ""

    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "oourafft OHOS adaptation is validated on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler(self, name, fallback):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        return executables.get(name) or fallback

    def build(self):
        apply_conandata_patches(self)
        cc = self._compiler("c", "clang")
        ar = os.path.join(os.path.dirname(cc), "llvm-ar")
        if not os.path.isfile(ar):
            ar = "ar"

        for lib, src in LIBS:
            obj = src + ".o"
            self.run('"{}" -O2 -fPIC -c {} -o {}'.format(cc, src, obj),
                     cwd=self.source_folder)
            self.run('"{}" rcs lib{}.a {}'.format(ar, lib, obj),
                     cwd=self.source_folder)

        # Build and run the upstream 1-D test suite.
        self.run('"{}" -O2 sample1/testxg.c libfft2d_fftsg.a -lm -o testxg'
                 .format(cc), cwd=self.source_folder)
        self.run('echo 64 | ./testxg > testxg.out', cwd=self.source_folder)
        with open(os.path.join(self.source_folder, "testxg.out")) as fh:
            out = fh.read()
        errs = re.findall(r"err=\s*([0-9.eE+-]+)", out)
        if len(errs) != 6:
            raise ConanException(
                "upstream testxg produced %d/6 checks:\n%s" % (len(errs), out))
        bad = [e for e in errs if float(e) > 1e-9]
        if bad:
            raise ConanException("upstream testxg errors too large: %r" % out)
        self.output.info("upstream testxg 6/6 checks passed (max err %s)"
                         % max(errs, key=float))

    def package(self):
        copy(self, "readme.txt", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        copy(self, "alloc.h", self.source_folder,
             os.path.join(self.package_folder, "include"))
        for lib in INSTALLED:
            copy(self, "lib%s.a" % lib, self.source_folder,
                 os.path.join(self.package_folder, "lib"))

    def package_info(self):
        # Dependents before dependencies so a plain "-l..." list links.
        self.cpp_info.libs = [
            "fft2d_fftsg2d",
            "fft2d_fftsg",
            "fft2d_alloc",
        ]
        self.cpp_info.system_libs = ["m"]
