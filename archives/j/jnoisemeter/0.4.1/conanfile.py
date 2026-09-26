#!/usr/bin/env python3
"""Conan recipe for jnoisemeter 0.4.1 (Fons Adriaensen).

Pure-Makefile project (source/Makefile): an X11 GUI noise-level meter that
attaches to a running JACK server as a client and shows ITU-R468 / IEC
225000 Type 1+2 / RMS / VU detections per channel. It builds one binary,
`jnoisemeter`. There is no configure script and no upstream test target.

OHOS portability notes (see notes.md):
  - The upstream Makefile locates FreeType with `pkgconf --cflags freetype2`;
    the patch replaces that probe with the $(PCONFCFL) slot so the headers
    come from the Conan packages instead of host pkg-config state.
  - The Makefile hardcodes `CXXFLAGS += -march=native`; the patch removes it
    so code generation is controlled by the toolchain named in the Conan
    profile (clang 15 on AArch64 rejects -march=native outright, and a
    native-tuned binary must not ship in a package).
  - OpenHarmony has no bare `install` on PATH; the patch parameterises
    INSTALL (default /bin/install, provided by toybox).
  - Upstream already links through `$(CXX)` and already uses `PREFIX ?=` /
    `BINDIR ?=`, so those lines need no portability change.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class JnoisemeterConan(ConanFile):
    name = "jnoisemeter"
    version = "0.4.1"
    package_type = "application"
    description = "X11 noise level meter driven by a JACK client"
    license = "GPL-2.0-or-later"
    homepage = "https://kokkinizita.linuxaudio.org/linuxaudio/"
    url = ""  # CI fills this

    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "jnoisemeter supports Linux and OHOS only"
            )
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "jnoisemeter supports OHOS armv8 only"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # jclient.cc / mainwin.cc / styles.cc are built on the clxclient X11
        # widget layer and the clthreads realtime thread classes; Xft.h pulls
        # in fontconfig, libxrender and FreeType through libxft's own
        # transitive interface, and xorgproto supplies the <X11/Xos.h> style
        # compatibility headers.
        self.requires("clxclient/3.9.2", transitive_headers=True)
        self.requires("clthreads/2.4.0", transitive_headers=True)
        self.requires("libxft/2.3.8", transitive_headers=True)
        self.requires("libx11/1.8.13", transitive_headers=True)
        self.requires("xorgproto/2025.1", transitive_headers=True)
        # jclient.cc calls jack_client_open() / jack_set_process_callback().
        self.requires("jack/1.9.22", transitive_headers=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        source_dir = os.path.join(self.source_folder, "source")
        # R33: the compiler must come from the Conan profile conf, never from
        # a bare shell CXX variable (empty on CI/release workers).
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cxx = compilers.get("cpp", "clang++") if compilers else "clang++"
        # Dependency include/lib directories are injected through the patched
        # $(PCONFCFL) slot and through LDFLAGS. CPPFLAGS is only ever appended
        # to by the Makefile, so the built-in -DVERSION and -MMD -MP survive
        # (VERSION is referenced by mainwin.cc and jnoisemeter.cc).
        pconfcfl = ""
        if str(self.settings.os) == "OHOS":
            # clthreads exposes CLTHREADS_NO_PTHREAD_CANCEL to OHOS consumers
            # because pthread_cancel is absent; a plain make build does not
            # read CMakeDeps, so the define is added here.
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
            'make -C "{}" -j1 CXX="{}" PCONFCFL="{}" LDFLAGS="{}" jnoisemeter'.format(
                source_dir, cxx, pconfcfl, ldflags
            )
        )
        # Upstream ships no test/check target: `make check` in source/ fails
        # with "No rule to make target 'check'. Stop." (only jnoisemeter,
        # install, uninstall and clean exist), so there is no test step here.
        # The consumer-side check lives in test_package/.

    def package(self):
        source_dir = os.path.join(self.source_folder, "source")
        # PREFIX=/ turns BINDIR into /bin, so the tool is staged under
        # <package>/bin by the patched $(INSTALL).
        self.run(
            'make -C "{}" install PREFIX=/ DESTDIR="{}"'.format(
                source_dir, self.package_folder
            )
        )
        copy(
            self,
            "COPYING",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        # Standalone tool: it exports no linkable library for consumers.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
