#!/usr/bin/env python3
"""Conan recipe — libgta 1.2.1 (Generic Tagged Array file format library).

libgta is a small, portable C library that implements the GTA file format
(streamable, out-of-core multidimensional arrays with tags).  Upstream ships
a release tarball with a pre-generated `configure`, so no autoreconf bootstrap
is needed (no automake/libtool tool_requires; the tarball's build-aux is used
as-is).

Build products (ground truth from `make install DESTDIR=...` exploration run):
  * lib/libgta.so* + lib/libgta.a   (libtool, SONAME libgta.so.1)
  * include/gta/{gta.h,gta.hpp,gta_version.h}
  * lib/pkgconfig/gta.pc
  * share/doc/libgta/example-*.c/.cpp
No executables are installed → library-only package, no commands.json (R38/PF8).

Dependencies: ZERO.  configure.ac only probes zlib/bz2/lzma behind the
*deprecated* `--with-compression` switch (default off, configure.ac:72-98) and
CMakeLists.txt declares no find_package for them either — the default build
has no external requirements.

OHOS adaptations (details in notes.md):
  * E007 family: the tarball ships config.guess/config.sub stamped 2018-02-24;
    `uname -s` reports `HarmonyOS`, so config.guess aborts ("unable to guess
    system type", rc=1) at `checking build system type`.  Fixed with whole-file
    patches to the 2026-05-17 GNU config release plus a `*:HarmonyOS:*:*` branch
    that emits `aarch64-unknown-linux-ohos` (the new config.sub accepts it).
  * E678 family (HMDFS): the autoconf 2.69 config-files machinery creates its
    scratch dir with `(umask 077 && mktemp -d "./confXXXXXX")`; HMDFS maps that
    to an unwritable 2700 directory (device-facts §一.10) and config.status dies
    with `can't create ./confXXXXXX/subs1.awk: Permission denied`.  Fixed by
    normalizing the mechanism in `configure` to `tmp=./conftmp` +
    `(umask 022 && mkdir -p "$tmp")` (fallback likewise), so the generated
    config.status inherits the fix.
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
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibgtaConan(ConanFile):
    name = "libgta"
    version = "1.2.1"
    description = ("libgta: portable C library for the Generic Tagged Array "
                   "(GTA) file format")
    license = "LGPL-2.1-or-later"  # COPYING = LGPL-2.1, src headers say "or any later version"
    homepage = "https://marlam.de/gta/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Zero dependencies: configure.ac only probes zlib/bz2/lzma behind the
        # deprecated `--with-compression` switch, which is OFF by default
        # (configure.ac:73-77 `compression="no "`), so AC_LIB_HAVE_LINKFLAGS is
        # never reached in the default build.  CMakeLists.txt likewise has no
        # third-party find_package (only an optional Doxygen for docs, which
        # the autotools entry does not require).
        pass

    def validate(self):
        # R32: settings.os must be checked against ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libgta is only supported on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R1 参数最少化: no extra configure args; the deprecated compression
        # feature stays at its upstream default (off) — zero dependencies.
        # Wire the `shared` option to libtool explicitly so exactly one flavor
        # is built (upstream default builds BOTH).
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--disable-shared")
            tc.configure_args.append("--enable-static")
        tc.generate()
        # Dependency injection (no-op with empty requirements()) — keeps the
        # container template contract: once a requires() is ever added here,
        # its -I/-L must reach configure or AC_CHECK_LIB probes go fake-green.
        AutotoolsDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # libtool .la wrappers embed absolute build paths — drop them.
        libdir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(libdir):
            for name in os.listdir(libdir):
                if name.endswith(".la"):
                    os.remove(os.path.join(libdir, name))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Ground truth from the exploration install tree: the shared object is
        # libgta.so (SONAME libgta.so.1) → cpp_info.libs = "gta", and the
        # installed pkg-config file is gta.pc (upstream src/gta.pc.in), so the
        # consumer-facing pkg_config_name must be "gta", not the recipe name.
        self.cpp_info.set_property("pkg_config_name", "gta")
        self.cpp_info.libs = ["gta"]
