#!/usr/bin/env python3
"""Conan recipe for libmaxminddb 1.13.3 — pure C MaxMind DB reader (autotools).

Products
--------
- libmaxminddb shared/static library (src/maxminddb.c, data-pool.c)
- mmdblookup CLI (bin/mmdblookup)
- public header include/maxminddb.h (+ generated include/maxminddb_config.h)
- pkg-config file lib/pkgconfig/libmaxminddb.pc

Build
-----
autotools: configure --host=... --prefix=... && make -j1 && make install DESTDIR=...

OHOS notes
----------
- The bundled config.sub already accepts the aarch64-linux-ohos triplet (no
  config.guess/config.sub patch needed).
- CI builds with the same OHOS profile on both host and build sides, so Conan's
  AutotoolsToolchain cannot detect a cross build and injects no triplet.
  An explicit ``--host=aarch64-linux-ohos`` makes configure treat this as a cross
  build (cross_compiling=yes): AC_C_BIGENDIAN then uses the compile-time BYTE_ORDER
  path instead of trying to execute an aarch64 binary on the x86_64 worker.
- ``make check`` is NOT run here: the check_PROGRAMS are aarch64 OHOS binaries and
  cannot be executed on the build worker (exec format error); they must be run on an
  OHOS device/emulator (test inventory in notes.md, R51).
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibMaxMindDBConan(ConanFile):
    name = "libmaxminddb"
    version = "1.13.3"
    description = "C library for reading MaxMind DB files (GeoIP2/GeoLite2), with mmdblookup CLI"
    license = "Apache-2.0"
    homepage = "https://github.com/maxmind/libmaxminddb"
    url = ""
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def validate(self):
        # R32: os check must be "in (Linux, OHOS)", not "== Linux"
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libmaxminddb is supported only on Linux/OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # libmaxminddb is NOT a system-name library, so dynamic is the Conan-managed
        # default (R26 applies only to system libs like zlib/ncurses on the platform).
        if not self.options.shared:
            tc.configure_args.extend(["--enable-static", "--disable-shared"])
        if str(self.settings.os) == "OHOS":
            # Build/host explicit triplets so configure never calls config.guess:
            # on a HarmonyOS (aarch64) build machine config.guess (2024-07-27)
            # cannot recognize "HarmonyOS" and aborts with
            # "configure: error: cannot guess build type" (E007-class). config.sub
            # accepts aarch64-linux-ohos -> aarch64-unknown-linux-ohos (rc=0).
            if not any(a.startswith("--host=") for a in tc.configure_args):
                tc.configure_args.append("--host=aarch64-linux-ohos")
            if not any(a.startswith("--build=") for a in tc.configure_args):
                tc.configure_args.append("--build=aarch64-linux-ohos")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # make check intentionally skipped: test binaries are aarch64 OHOS and cannot
        # run on the x86_64 CI worker. Run them on target instead (see notes.md).

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Drop libtool *.la wrappers (Conan 2 copy() has no delete= argument).
        for la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(la)

    def package_info(self):
        self.cpp_info.libs = ["maxminddb"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
        # configure may pull in libm (AC_SEARCH_LIBS for fabs/fabsf)
        self.cpp_info.system_libs = ["m"]
