#!/usr/bin/env python3
"""Conan recipe for jpegoptim 1.4.7 - lossless JPEG optimizer/compressor (CLI).

jpegoptim rewrites JPEG files in place: it optimizes the Huffman tables,
optionally converts to progressive encoding, and can strip metadata
(COM/Exif/IPTC/XMP sections).  It is a single-binary Autotools project that
links against libjpeg.

Dependencies:
  - libjpeg/10  (IJG JPEG codec, published on ohpcd)

OHOS adaptations (patches in conandata.yml):
  - 0001-configure.patch: config.status creates its scratch directory with
    `umask 077`.  On HMDFS the running process UID differs from the mapped
    directory owner, so the resulting directory is not even writable by its
    owner (E011), and config.status dies with
    "can't create ./confXXXXXX/subs1.awk: Permission denied".
  - 0002-tools-config.guess.patch / 0003-tools-config.sub.patch: the tarball
    ships a 2012-vintage config.guess/config.sub pair that does not know the
    "*-linux-ohos" namespace, so `./configure` aborts with
    "cannot guess build type; you must specify one".

Layout note: jpegoptim ships a hand-written Makefile.in with no VPATH
support - its compile rule is `$(CC) $(CFLAGS) -c $<` with no -I for the
build directory - so `#include "config.h"` only resolves for an in-source
build.  Source and build folders are therefore kept identical (same approach
as ncurses).
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain


class JpegoptimConan(ConanFile):
    name = "jpegoptim"
    version = "1.4.7"
    description = "Utility to optimize/compress JPEG files losslessly (command-line)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/tjko/jpegoptim"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # CLI tool, not a library (R38: commands.json declared at software level)
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libjpeg/10")

    def validate(self):
        # R32: settings.os must be checked against ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"jpegoptim is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        self.folders.source = "src"
        self.folders.build = "src"
        self.folders.generators = "build-generators"

    def source(self):
        # The fallback codeload URL has no archive extension, so name the
        # download explicitly or Conan infers the wrong format.
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="jpegoptim-1.4.7.tar.gz")
        apply_conandata_patches(self)

    def generate(self):
        # AutotoolsDeps feeds -I/-L/-l from libjpeg into configure and make.
        deps = AutotoolsDeps(self)
        deps.generate()
        tc = AutotoolsToolchain(self)
        tc.generate()
        # configure probes libjpeg by compiling and running small programs.
        # The OHOS loader has no default search path for libraries living in
        # the Conan cache, so the dependency libdirs must be exported to the
        # build scope (E467 signature otherwise).
        env = Environment()
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", libdir)
        env.vars(self, scope="build").save_script("conanbuild_runpath")

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        # R9: single job - parallel make needs a jobserver fifo, which HMDFS
        # refuses to create (E074).
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Standalone binary, no library info to export
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
