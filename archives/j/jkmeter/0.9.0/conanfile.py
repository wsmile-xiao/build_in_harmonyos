#!/usr/bin/env python3
"""Conan recipe for jkmeter 0.9.0 (Fons Adriaensen).

Pure-Makefile project (source/Makefile) that builds a single JACK audio
metering application:
  - `jkmeter`  — K-System (K12/K14/K20) + stereo correlation meter, X11 GUI.
                 Links clxclient/clthreads/jack/png/Xft/X11.

No configure script and no upstream test target. The portability patch
removes -march=native, replaces the `pkg-config --cflags freetype2` probe
with the $(PCONFCFL) injection slot (Conan supplies every include/lib search
path explicitly), and parameterizes INSTALL for OHOS. The linker is $(CXX)
from the Conan profile (R33: key "cpp" in tools.build:compiler_executables).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class JkmeterConan(ConanFile):
    name = "jkmeter"
    version = "0.9.0"
    package_type = "application"
    description = "K-System K12/K14/K20 loudness and correlation meter for JACK (X11 GUI)"
    license = "GPL-2.0-or-later"
    homepage = "https://kokkinizita.linuxaudio.org/linuxaudio/"
    url = ""  # CI fills this

    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("jkmeter supports Linux and OHOS only")
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("jkmeter supports OHOS armv8 only")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # jkmeter links clxclient/clthreads/jack/png/Xft/X11 and compiles
        # against sndfile.h (types only, upstream links no -lsndfile).
        self.requires("clxclient/3.9.2", transitive_headers=True)
        self.requires("clthreads/2.4.0", transitive_headers=True)
        self.requires("jack/1.9.22", transitive_headers=True)
        self.requires("libpng/1.6.58.3", transitive_headers=True)
        self.requires("libsndfile/1.2.2", transitive_headers=True)
        self.requires("freetype/2.14.3", transitive_headers=True)
        # X11 GUI headers: declared explicitly (mirrors the aliki/clxclient
        # OHOS pattern) so the include directories are guaranteed in the
        # dependency graph we iterate over in build().
        self.requires("libxft/2.3.8", transitive_headers=True)
        self.requires("libx11/1.8.13", transitive_headers=True)
        self.requires("xorgproto/2025.1", transitive_headers=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        source_dir = os.path.join(self.source_folder, "source")
        # R33: compiler must come from the Conan profile conf, never a bare
        # shell ${CXX} (empty on CI/release workers). The profile key is
        # "cpp" (not "cxx") in this repository.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = compilers.get("cpp", "clang++") if compilers else "clang++"
        # Collect include/lib search paths from every declared dependency,
        # injected through the Makefile's $(PCONFCFL) slot so the built-in
        # -DVERSION/-DSHARED definitions and the -l* link list stay intact.
        pconfcfl = " -I."
        if str(self.settings.os) == "OHOS":
            # clthreads' package_info defines CLTHREADS_NO_PTHREAD_CANCEL for
            # OHOS consumers (pthread_cancel is absent); a raw make build does
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
        # "No rule to make target 'check'"); see test_package/ for the
        # consumer-side smoke test.

    def package(self):
        source_dir = os.path.join(self.source_folder, "source")
        # PREFIX=/ collapses the Makefile's $(PREFIX)/bin and
        # $(PREFIX)/share/jkmeter onto the Conan package root; the patched
        # $(INSTALL) variable makes the bare-Makefile install steps portable.
        self.run(
            'make -C "{}" install PREFIX=/ DESTDIR="{}"'.format(
                source_dir, self.package_folder
            )
        )

    def package_info(self):
        # jkmeter is a standalone tool; it exports no libraries for consumers.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
