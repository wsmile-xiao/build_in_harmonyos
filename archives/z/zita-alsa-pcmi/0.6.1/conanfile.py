#!/usr/bin/env python3
"""Conan recipe for zita-alsa-pcmi 0.6.1 (Fons Adriaensen).

Pure-Makefile project (source/Makefile), no configure script, no upstream
test target. Builds the shared library libzita-alsa-pcmi.so.0.6.1 and the
public header zita-alsa-pcmi.h against the alsa-lib dependency.

OHOS portability notes (see notes.md):
  - The upstream Makefile hardcodes `CXXFLAGS += -march=native`; the
    portability patch removes it so the toolchain from the Conan profile
    (tools.build:compiler_executables) controls code generation.
  - OpenHarmony has no bare `install`/`ldconfig` on PATH; the patch
    parameterises INSTALL (default /bin/install, toybox) and drops ldconfig.
  - The install target now emits the full symlink chain
    (libzita-alsa-pcmi.so -> .so.0 -> .so.0.6.1) so the runtime loader can
    resolve the SONAME and consumers can link with -lzita-alsa-pcmi.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class ZitaAlsaPcmiConan(ConanFile):
    name = "zita-alsa-pcmi"
    version = "0.6.1"
    package_type = "library"
    description = "C++ library providing easy access to ALSA PCM devices"
    license = "GPL-3.0-or-later"
    homepage = "https://kokkinizita.linuxaudio.org/linuxaudio/"
    url = ""  # CI fills this

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("zita-alsa-pcmi supports Linux and OHOS only")
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("zita-alsa-pcmi supports OHOS armv8 only")
        if not self.options.shared:
            raise ConanInvalidConfiguration("zita-alsa-pcmi 0.6.1 only builds a shared library")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("alsa-lib/1.2.16")

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
        alsa = self.dependencies["alsa-lib"]
        cppflags = "-D_REENTRANT -D_POSIX_PTHREAD_SEMANTICS"
        cppflags += " -I" + os.path.join(alsa.package_folder, "include")
        cxxflags = "-O2 -Wall -fPIC"
        ldflags = "-L" + os.path.join(alsa.package_folder, "lib")
        self.run(
            'make -C "{}" -j1 CXX="{}" CXXFLAGS="{}" CPPFLAGS="{}" LDFLAGS="{}" '
            "libzita-alsa-pcmi.so.0.6.1".format(
                source_dir, cxx, cxxflags, cppflags, ldflags
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
        self.cpp_info.libs = ["zita-alsa-pcmi"]
        # The packaged .so links libasound.so (NEEDED) and its public header
        # includes <alsa/asoundlib.h>; consumers must inherit alsa-lib's
        # include dirs and the ALSA::asound link interface.
        self.cpp_info.requires = ["alsa-lib::asound"]
        self.cpp_info.set_property("cmake_file_name", "zita-alsa-pcmi")
        self.cpp_info.set_property("cmake_target_name", "zita-alsa-pcmi::zita-alsa-pcmi")
