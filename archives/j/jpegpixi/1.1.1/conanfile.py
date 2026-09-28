#!/usr/bin/env python3
"""Conan recipe for jpegpixi 1.1.1 — JPEG pixel interpolation CLI tool.

jpegpixi reads a JPEG file, interpolates dead/hot pixels at given coordinates
and writes the result re-encoding only the affected blocks. Autotools project
(autoconf 2.59 / automake 1.9, tarball ships pre-generated configure).

Dependency:
  - libjpeg/10 (published on ohpcd; MD_PATH macro probes jpeglib.h + -ljpeg;
    flags come from AutotoolsDeps env injection, no /usr hardcoded paths)

OHOS adaptations:
  - --disable-nls: MD_NLS degrades cleanly when gettext/libintl is absent.
  - Tarball ships pre-generated OPAG outputs (optpixi.c/opthotp.c); tar mtimes
    keep .opag older than generated sources, so make never invokes the missing
    `opag` generator (verified: 2005-11-21 04:28/04:30 vs 04:40).
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout


class JpegpixiConan(ConanFile):
    name = "jpegpixi"
    version = "1.1.1"
    description = "Interpolate pixels in JPEG images (fix dead/hot pixels, re-encode only affected blocks)"
    license = "GPL-2.0-or-later"
    homepage = "http://www.zero-based.org/software/jpegpixi/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libjpeg/10")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"jpegpixi only supports Linux/OHOS, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # E011/E114: strip `umask 077` from confstat temp-dir creation — HMDFS
        # setgid makes drwx--S--- dirs unwritable, config.status then fails.
        apply_conandata_patches(self)

    def generate(self):
        # AutotoolsDeps: feed libjpeg -I/-L/-l into configure/make env (R49-conformant)
        deps = AutotoolsDeps(self)
        deps.generate()
        tc = AutotoolsToolchain(self)
        # MD_NLS: no gettext/libintl on OHOS -> disable cleanly instead of warn-degrade
        tc.configure_args.append("--disable-nls")
        tc.generate()
        # configure conftests only compile/link (no run), but keep dep lib dirs on
        # the loader path so any test execution of built binaries still works.
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
        # CLI tools: bin/jpegpixi + bin/jpeghotp, no library info
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
