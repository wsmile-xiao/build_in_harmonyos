#!/usr/bin/env python3
"""Conan recipe for gdnsd 3.8.2 - Geographic Authoritative DNS server.

gdnsd is an authoritative-only DNS server. It produces command-line executables
(gdnsd, gdnsdctl, gdnsd_geoip_test, gdnsd_extmon_helper).

Adaptation notes:
- Source is the official release tarball (make dist output): it ships a
  pre-generated configure script and the ragel-generated C sources (e.g.
  libgdnsd/vscf.c), so neither ragel nor autoreconf/automake/libtool are
  needed at build time.
- 3 patches guard pthread_setcanceltype calls with
  #ifndef HAVE_PTHREAD_SETCANCELTYPE: OHOS musl libc does not provide
  pthread_setcanceltype (no libc symbol, not declared in pthread.h), and
  upstream's configure never defines that macro, so the guarded calls are
  skipped on OHOS (and, since the macro is never defined anywhere, on other
  platforms too - see notes.md for the impact assessment).
- Patch 0004 teaches the shipped config.sub (timestamp 2022-01-03, predates
  ohos) to accept linux-ohos triplets; --build/--host are passed explicitly
  because config.guess cannot detect HarmonyOS (uname -s = "HarmonyOS").
- Patch 0005 replaces mktemp -d with mkdir -p in the shipped configure: on
  HMDFS, directories created by mktemp get mode 0700 and all writes inside
  them fail with EACCES, breaking every configure compile test (plain mkdir
  gets a usable mode on HMDFS).
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class GdnsdConan(ConanFile):
    name = "gdnsd"
    version = "3.8.2"
    description = "gdnsd - Geographic Authoritative DNS server"
    license = "GPL-3.0-or-later"
    homepage = "https://gdnsd.org"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # gdnsd 3.8.2 links only against these (upstream Makefile.am LDADD:
        # -lm -lurcu-qsbr -lev -lsodium); it does not use zlib or openssl.
        self.requires("libev/4.33")
        self.requires("userspace-rcu/0.15.6")
        self.requires("libsodium/1.0.22")

    def configure(self):
        # The only published libev/4.33 binary is shared; a shared libev.so
        # makes the produced executables depend on LD_LIBRARY_PATH setup to
        # run (configure's runtime test and the L2 smoke test both fail with
        # "Error loading shared library libev.so"). Force static so the
        # gdnsd binaries are self-contained (libsodium/urcu are static).
        self.options["libev"].shared = False

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.settings.os == "OHOS":
            if self.settings.arch != "armv8":
                raise ConanInvalidConfiguration(
                    "gdnsd/3.8.2 currently supports only OHOS armv8"
                )
            # config.guess cannot detect HarmonyOS (uname -s = "HarmonyOS")
            # and the shipped config.sub (patched by 0004) validates
            # linux-ohos triplets. build == host keeps this a native build,
            # so AC_RUN_IFELSE checks still execute on the device.
            tc.configure_args += [
                "--build=aarch64-linux-ohos",
                "--host=aarch64-linux-ohos",
            ]
        tc.generate()
        # gdnsd's configure does not use pkg-config for its dependencies
        # (Makefile.am hardcodes -lev -lurcu-qsbr -lsodium), so the conan
        # dependencies' -I/-L/-l flags are injected via AutotoolsDeps.
        AutotoolsDeps(self).generate()

    def build(self):
        # All source modifications are declared patches in conandata.yml
        # (0001-0005), including the HMDFS mktemp workaround (0005) so that
        # upstream drift breaks patch application loudly instead of silently.
        apply_conandata_patches(self)

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j2"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # gdnsd is an application - expose bindirs and sbindirs
        self.cpp_info.bindirs = ["bin", "sbin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.resdirs = ["share"]
