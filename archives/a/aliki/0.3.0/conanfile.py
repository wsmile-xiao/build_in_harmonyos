#!/usr/bin/env python3
"""Conan recipe for aliki 0.3.0 (Fons Adriaensen).

Pure-Makefile project (source/Makefile) that builds two audio measurement
tools:
  - `aliki`     — the X11 GUI for impulse-response measurement (sine sweep +
                  deconvolution). Links clxclient/clthreads/sndfile/fftw3f/
                  Xft/X11.
  - `aliki-rt`  — the real-time capture program. Links zita-alsa-pcmi/
                  clthreads/sndfile/jack/alsa.

No configure script and no upstream test target. The portability patch
removes -march=native and the hardcoded /usr/include/freetype2 and
/usr/X11R6 paths, parameterises INSTALL for OHOS, and uses $(CXX) from the
Conan profile (R33).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class AlikiConan(ConanFile):
    name = "aliki"
    version = "0.3.0"
    package_type = "application"
    description = "Impulse response measurement tool (sine sweep + deconvolution)"
    license = "GPL-3.0-or-later"
    homepage = "https://kokkinizita.linuxaudio.org/linuxaudio/"
    url = ""  # CI fills this

    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("aliki supports Linux and OHOS only")
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("aliki supports OHOS armv8 only")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # aliki (GUI)
        self.requires("clxclient/3.9.2", transitive_headers=True)
        self.requires("clthreads/2.4.0", transitive_headers=True)
        self.requires("libsndfile/1.2.2", transitive_headers=True)
        self.requires("fftw3f/3.3.9", transitive_headers=True)
        self.requires("libxft/2.3.8", transitive_headers=True)
        self.requires("libx11/1.8.13", transitive_headers=True)
        self.requires("xorgproto/2025.1", transitive_headers=True)
        # aliki-rt
        self.requires("zita-alsa-pcmi/0.6.1", transitive_headers=True)
        self.requires("jack/1.9.22", transitive_headers=True)
        self.requires("alsa-lib/1.2.16", transitive_headers=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        source_dir = os.path.join(self.source_folder, "source")
        # R33: compiler must come from the Conan profile conf, never a bare
        # shell ${CXX} (empty on CI/release workers).
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = compilers.get("cpp", "clang++") if compilers else "clang++"
        # Collect include/lib search paths from every declared dependency,
        # injected through the Makefile's $(PCONFCFL) slot so the built-in
        # -DVERSION/-DPREFIX definitions stay intact.
        pconfcfl = " -I."
        if str(self.settings.os) == "OHOS":
            # clthreads' package_info defines CLTHREADS_NO_PTHREAD_CANCEL for
            # OHOS consumers (pthread_cancel is absent); our make build does
            # not consume that define through CMakeDeps, so add it manually.
            pconfcfl += " -DCLTHREADS_NO_PTHREAD_CANCEL"
        ldflags = ""
        for _, dependency in self.dependencies.items():
            if not dependency.package_folder:
                continue
            for incdir in dependency.cpp_info.includedirs:
                path = incdir
                if not os.path.isabs(path):
                    path = os.path.join(dependency.package_folder, incdir)
                pconfcfl += " -I" + path
            for libdir in dependency.cpp_info.libdirs:
                path = libdir
                if not os.path.isabs(path):
                    path = os.path.join(dependency.package_folder, libdir)
                ldflags += " -L" + path
        self.run(
            'make -C "{}" -j1 CXX="{}" PCONFCFL="{}" LDFLAGS="{}" all'.format(
                source_dir, cxx, pconfcfl, ldflags
            )
        )
        # Upstream ships no test/check target (`make check` fails with
        # "No rule to make target 'check'"); the recipe therefore has no
        # test step here. See test_package/ for the consumer-side test.

    def package(self):
        source_dir = os.path.join(self.source_folder, "source")
        # LIBDIR=lib fixes the Makefile's $(SUFFIX)-derived lib path.
        self.run(
            'make -C "{}" install PREFIX=/ LIBDIR=lib DESTDIR="{}"'.format(
                source_dir, self.package_folder
            )
        )

    def package_info(self):
        # aliki is a standalone tool; it exports no libraries for consumers.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
