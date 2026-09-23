#!/usr/bin/env python3
"""Conan recipe — fftw 2.1.5 (autotools, single-precision prefixed libs for clipper).

FFTW2 (legacy 2003 release) built with --enable-float --enable-type-prefix so the
installed libraries are libsfftw/libsrfftw with sfftw.h/srfftw.h headers — exactly
what CCP4 clipper (fftmap.cpp includes <srfftw.h>/<rfftw.h>) requires.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class FftwConan(ConanFile):
    name = "fftw"
    version = "2.1.5"
    description = "FFTW2 single-precision (sfftw/srfftw) legacy library for CCP4 clipper"
    license = "GPL-2.0-or-later"
    homepage = "https://www.fftw.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("fftw", "fft", "sfftw", "srfftw", "crystallography", "clipper")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Single precision with 's' type-prefix → libsfftw.a / libsrfftw.a + sfftw.h / srfftw.h
        tc.configure_args.append("--enable-float")
        tc.configure_args.append("--enable-type-prefix")
        # FFTW2 old config.guess cannot guess HarmonyOS; patched via patches/
        # R26: static by default (system-name adjacent library, avoid polluting /lib)
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # threads/mpi not needed by downstream (clipper)
        tc.configure_args.append("--disable-threads")
        tc.configure_args.append("--disable-mpi")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # E490: HMDFS transfer may strip execute bits on autotools helper scripts
        for _helper in ("configure", "config.guess", "config.sub", "install-sh", "missing"):
            _p = os.path.join(self.source_folder, _helper)
            if os.path.isfile(_p):
                os.chmod(_p, os.stat(_p).st_mode | 0o111)
        autotools = Autotools(self)
        autotools.configure()
        # Only build the two core libraries. The top-level SUBDIRS also contains
        # doc/threads/mpi which is slow/not needed; tests are built separately.
        self.run("make -C fftw -j1", cwd=self.build_folder)
        self.run("make -C rfftw -j1", cwd=self.build_folder)

    def package(self):
        # Install only fftw + rfftw core libs/headers (skip doc/threads/mpi).
        self.run("make -C fftw install DESTDIR={}".format(self.package_folder), cwd=self.build_folder)
        self.run("make -C rfftw install DESTDIR={}".format(self.package_folder), cwd=self.build_folder)

    def package_info(self):
        self.cpp_info.libs = ["srfftw", "sfftw"]
        self.cpp_info.system_libs = ["m"]
