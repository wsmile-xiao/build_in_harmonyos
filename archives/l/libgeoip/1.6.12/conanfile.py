#!/usr/bin/env python3
"""Conan recipe for libgeoip 1.6.12 — MaxMind GeoIP Legacy C library.

libGeoIP is the legacy GeoIP C library (geoip-api-c): non-intrusive IP
geolocation lookups from local MaxMind database files (.dat format).
It ships one shared/static library (libGeoIP) plus two CLI lookup tools
(geoiplookup / geoiplookup6).  GeoIP2 (libmaxminddb) is the successor
project — a different piece of software.

Build: Autotools.  The release tarball ships configure.ac but NO
pre-generated `configure`, so build() bootstraps with `autoreconf -fiv`
(automake/libtool pulled in via tool_requires, same approach as
codecrypt 1.8).

Dependencies: none.  The library itself has zero mandatory deps (no
zlib — the .dat reader is raw stdio + mmap).  Database files (GeoIP.dat
etc.) are runtime data supplied by the user and are intentionally NOT
packaged; test_package extracts the sample GeoIP.dat that upstream
ships inside the source tarball.

OHOS adaptations (all build-system level, no source patches needed):
  - generated `configure` is patched in-tree to drop `umask 077` from
    the config.status temp-dir creation (E114: HMDFS turns a 0700 temp
    dir into an unwritable drwx--S--- dir);
  - triplet passed explicitly (--build/--host aarch64-unknown-linux-ohos)
    so configure never runs the config.guess probe (HarmonyOS uname -s
    is not recognized by stock config.guess);
  - make runs with -j1 (E074: HMDFS jobserver fifo EPERM);
  - no source-level patch required: all configure checks (pread, mmap,
    vasprintf, gethostbyname_r, ...) pass on musl/OHOS as-is.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (get, apply_conandata_patches,
                               export_conandata_patches, replace_in_file)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibgeoipConan(ConanFile):
    name = "libgeoip"
    version = "1.6.12"
    description = ("MaxMind GeoIP Legacy C library (libGeoIP): IP "
                   "geolocation lookups from local .dat databases, "
                   "plus geoiplookup/geoiplookup6 CLI tools")
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/maxmind/geoip-api-c"
    url = "https://github.com/maxmind/geoip-api-c"

    # Library + CLI tools: cpp_info.libs carries libGeoIP; bindirs carries
    # geoiplookup/geoiplookup6 (commands.json declared at software level).
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
        # Pure C project; drop the profile C++ std so it is not injected
        self.settings.rm_safe("compiler.cppstd")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libgeoip is only supported on Linux/OHOS, not "
                + str(self.settings.os))

    def build_requirements(self):
        # The tarball ships no `configure`; autoreconf needs the full
        # autotools suite.  The build host only has autoconf under
        # /data/service/hnp/bin, so pull in automake and libtool as
        # tool_requires (same approach as codecrypt 1.8).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def export_sources(self):
        # R1: patches are declared in conandata.yml (currently none — zero
        # source-level patch needed for OHOS); export_conandata_patches
        # keeps future patch additions wiring-correct.
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # No source patches for OHOS (patches: {} in conandata.yml); the
        # apply call is kept for wiring correctness (no-op when empty).
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--disable-shared")
            tc.configure_args.append("--enable-static")
        # config.guess cannot identify HarmonyOS; pass the triplet
        # explicitly so configure never runs the config.guess probe
        # (config.sub supports *-linux-ohos).
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        tc.generate()

    def build(self):
        # Bootstrap: the tarball ships no `configure`; bootstrap script
        # runs `autoreconf -fiv`.  chmod first: tarball extracts with
        # -rwxrwx--- and the CI user lacks the group bit (E126).
        bootstrap = os.path.join(self.source_folder, "bootstrap")
        if os.path.isfile(bootstrap):
            os.chmod(bootstrap, 0o755)
            self.run("sh bootstrap", cwd=self.source_folder, env="conanbuild")
        else:  # fallback if the bootstrap script is ever dropped
            self.run("autoreconf -fiv", cwd=self.source_folder,
                     env="conanbuild")

        # E114: drop umask 077 from the generated configure (HMDFS forces
        # setgid; `umask 077 && mktemp -d` creates a drwx--S--- temp dir
        # that is not writable even by its owner, breaking config.status).
        _conf = os.path.join(self.source_folder, "configure")
        replace_in_file(self, _conf,
                        'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&',
                        'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null` &&')
        replace_in_file(self, _conf,
                        '  tmp=./conf$$-$RANDOM\n  (umask 077 && mkdir "$tmp")',
                        '  tmp=./conf$$-$RANDOM\n  mkdir "$tmp"')

        autotools = Autotools(self)
        autotools.configure()
        # R9/E074: single job — parallel make hits HMDFS jobserver fifo EPERM
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["GeoIP"]
        self.cpp_info.bindirs = ["bin"]
        # pkg-config module name (geoip.pc) for downstream autotools users
        self.cpp_info.set_property("pkg_config_name", "geoip")
