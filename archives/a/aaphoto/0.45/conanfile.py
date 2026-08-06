#!/usr/bin/env python3
"""Conan recipe for aaphoto 0.45 — automatic photo color-correction CLI tool.

aaphoto is a small command-line tool that automatically adjusts the colors of
photos (contrast, gamma, color balance, saturation).  It is a single-binary
Autotools project (aaphoto.c includes aaio.c/aargb.c/aaresize.c).

Dependencies:
  - libjpeg/10   (JPEG codec, published on ohpcd)
  - libpng/1.6.58 (PNG codec, published on ohpcd; pulls zlib/1.3.1.1 transitively)
  - OpenMP       — the Makefile hardcodes GCC's `-lgomp`; on OHOS we build with
                   clang where `-fopenmp` auto-links the OHOS SDK's `libomp`.
                   Makefile.am/Makefile.in patches drop the `-lgomp` flag.

OHOS adaptations (patches in conandata.yml):
  - configure: remove `umask 077` from config.status temp-dir creation
    (E114 — HMDFS forces setgid and a drwx--S--- dir is not writable by its owner).
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout


class AaphotoConan(ConanFile):
    name = "aaphoto"
    version = "0.45"
    description = "Auto Adjust Photo - automatic color correction of photos (command-line)"
    license = "GPL-3.0-or-later"
    homepage = "http://log69.com/aaphoto_en.html"
    url = ""  # CI fills this

    # CLI tool, not a library (R38: commands.json declared at software level)
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # zlib comes transitively via libpng (zlib/1.3.1.1)
        self.requires("libjpeg/10")
        self.requires("libpng/1.6.58")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"aaphoto is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        # AutotoolsDeps: feed -I/-L/-l from libjpeg/libpng/zlib into configure/make
        deps = AutotoolsDeps(self)
        deps.generate()
        tc = AutotoolsToolchain(self)
        tc.generate()
        # OHOS loader has no default search path for conan-cached shared libs
        # (libpng16.so is shared-only). configure's conftest runs compiled
        # programs, which fails with "Error loading shared library libpng16.so.16"
        # unless LD_LIBRARY_PATH points at the dependency lib dirs.
        env = Environment()
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", libdir)
        env.vars(self, scope="build").save_script("conanbuild_runpath")

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        # R9: single job — parallel make hits HMDFS jobserver fifo EPERM (E074)
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Standalone binary, no C++/library info
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
