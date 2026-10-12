#!/usr/bin/env python3
"""Conan recipe for zita-lrx 0.1.2 (Fons Adriaensen).

Pure-Makefile project (source/Makefile) that builds one JACK command line
application:

  - `zita-lrx` — 2/3/4-band 4th-order Linkwitz-Riley/Butterworth crossover
                 filter for up to 16 channels, driven by an OSC-style text
                 config file. Links clthreads/jack.

No configure script and no upstream test target. The portability patch
removes -march=native, parameterises INSTALL for OHOS, and exposes the
PCONFCFL include slot so the built-in -DVERSION definition stays intact.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class ZitaLrxConan(ConanFile):
    name = "zita-lrx"
    version = "0.1.2"
    package_type = "application"
    description = "Command line JACK application providing 2, 3, or 4-band 4th-order crossover filters"
    license = "GPL-3.0-or-later"
    homepage = "https://kokkinizita.linuxaudio.org/linuxaudio/"
    url = "https://kokkinizita.linuxaudio.org/linuxaudio/"

    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("zita-lrx supports Linux and OHOS only")
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("zita-lrx supports OHOS armv8 only")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("clthreads/2.4.0", transitive_headers=True)
        self.requires("jack/1.9.22", transitive_headers=True)

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
        # -DVERSION definition stays intact.
        pconfcfl = " -I."
        if str(self.settings.os) == "OHOS":
            # clthreads' OHOS build avoids pthread_cancel (absent on OHOS
            # musl); the make build does not consume package_info defines
            # through CMakeDeps, so pass the guard macro manually.
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
        self.run(
            'make -C "{}" install PREFIX=/ DESTDIR="{}"'.format(
                source_dir, self.package_folder
            )
        )

    def package_info(self):
        # zita-lrx is a standalone tool; it exports no libraries for consumers.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
