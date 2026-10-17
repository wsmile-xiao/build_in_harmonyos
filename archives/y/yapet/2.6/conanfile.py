#!/usr/bin/env python3
"""Conan recipe — yapet 2.6 (Yet Another Password Encryption Tool) for HarmonyOS PC.

YAPET is a curses based password manager that stores records encrypted
(Blowfish / AES-256 via OpenSSL EVP, key derivation via Argon2) in a single
`.pet` file.  Upstream ships a release tarball with a pre-generated
`configure`, so no autoreconf bootstrap is needed.

Build products: `bin/yapet`, `bin/csv2yapet`, `bin/yapet2csv` (verified by
`make install DESTDIR=...`: only `bin/` + `share/` land in the tree).  The
bundled curses widget library `libyacurs` (AC_CONFIG_SUBDIRS sub-project) is
built and statically linked into the three CLI tools but deliberately NOT
installed: the top-level configure unconditionally appends `--disable-install`
to the sub-configure's arguments (configure.ac:143-144), so it goes through
`noinst_LTLIBRARIES` / `noinst_HEADERS`.

OHOS adaptations (details in notes.md):
  * E007 family — the tarball ships `config.guess`/`config.sub` stamped
    2018-08-29 (two copies: `build-aux/` and `libyacurs/build-aux/`).  Both
    `configure` scripts call `config.guess` for the build alias (no
    `--build`/`--host` is passed, R1), and `uname -s` reports `HarmonyOS`,
    so the guess fails and configure aborts.  Fixed with whole-file patches
    to the 2026-05-17 GNU config release plus a HarmonyOS branch that emits
    `aarch64-unknown-linux-ohos` (the new config.sub accepts that triplet).
  * `PKG_CHECK_MODULES([ARGON2], [libargon2])` expects the pkg-config module
    name `libargon2`, while the conan `argon2` recipe has no
    `pkg_config_name` property (would emit `argon2.pc`).  Resolved with the
    documented consumer override `PkgConfigDeps.set_property()` instead of
    env-var plumbing or a hand written .pc shim (see notes.md 问题表 #2 for
    the three-way trade-off).
  * `msgfmt` (AM_GNU_GETTEXT([external])) is provided via
    `tool_requires("gettext/...")`: the device finds it in harmonybrew but
    the CI worker PATH does not include harmonybrew (device-facts §一.4).
  * Upstream `tests/converters/check-local` hardcodes `/tmp/...` fixture
    paths; `/tmp` is read-only on OHOS, so the fixture paths move into the
    build directory (declared in the PR as an upstream test modification).
  * `tests/preload/check-local` is gated by the `istty` helper: without a
    tty the whole block is skipped by upstream's own logic — counted as
    SKIP with attribution, not as PASS.
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
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.env import VirtualBuildEnv
from conan.tools.layout import basic_layout


class YapetConan(ConanFile):
    name = "yapet"
    version = "2.6"
    description = ("Yet Another Password Encryption Tool: curses based password "
                   "manager with OpenSSL (Blowfish/AES-256) and Argon2 encryption")
    license = "GPL-3.0-or-later"
    homepage = "https://yapet.guengel.ch/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"  # ground truth: `make install` ships bin/ + share/ only
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # configure.ac: PKG_CHECK_MODULES([CPPUNIT], [cppunit]) and
        # PKG_CHECK_MODULES([ARGON2], [libargon2]) are unconditional, and
        # AX_CHECK_OPENSSL aborts without OpenSSL — all three are hard deps.
        # run=True keeps openssl present in the consumer graph (test_package /
        # conanrun): without it openssl is a skipped binary there and
        # package_info()'s self.dependencies["openssl"].package_folder is None
        # ("Error in package_info() ... not NoneType", G2实测). ppp/2.5.2:35
        # uses the same trait for the same reason.
        self.requires("openssl/3.0.21", run=True)
        self.requires("argon2/20190702")
        self.requires("ncurses/6.5")
        # cppunit links into the check_PROGRAMS only, but configure requires
        # its pkg-config module on every run (unconditional PKG_CHECK_MODULES).
        # Declared as a regular requirement (repo precedent: arx-libertatis
        # "for BUILD_TESTS") so PkgConfigDeps always emits `cppunit.pc`.
        self.requires("cppunit/1.15.1")

    def build_requirements(self):
        # AM_GNU_GETTEXT([external]) needs msgfmt at configure/make time;
        # the CI worker PATH has no harmonybrew (device-facts §一.4).
        self.tool_requires("gettext/0.22.5.1")

    def validate(self):
        # R32: settings.os must be checked against ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "yapet is only supported on Linux/OHOS, not " + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Do NOT pass --disable-shared here.  The bundled libyacurs preloadlib
        # hard-codes `-shared` into its `libtool --mode=compile` rule
        # (libyacurs/tests/preloadlib/Makefile.am:16), so a libtool configured
        # with --disable-shared aborts that compile with "cannot build a shared
        # library" — and libtool 2.4.6 then hides the real error behind
        # `func__fatal_error: command not found` because its own
        # func_fatal_configuration() calls a function it never defines
        # (create.log evidence: G2 build failed at libyacurs/tests/preloadlib).
        # Shared/static cannot affect the deliverable anyway: libyacurs is
        # noinst (top-level configure.ac:143-144 injects --disable-install), so
        # nothing from it is installed, and the three CLI tools statically link
        # the convenience library either way (readelf: NEEDED = libc only).
        # Leaving it unset keeps configure identical to the validated
        # exploration run (shared=yes / static=yes, all steps green).
        tc.extra_cflags.append("-fPIC")  # matches the exploration toolchain
        # PKG_CHECK_MODULES (cppunit / libargon2) resolves through pkg-config;
        # PkgConfigDeps writes the .pc files into the generators folder, which
        # is not on PKG_CONFIG_PATH unless we add it here.
        env = tc.environment()
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        tc.generate(env=env)

        # AutotoolsDeps: translate dependency cpp_info into CPPFLAGS/LDFLAGS.
        # Without it AX_CHECK_OPENSSL and libyacurs' ax_with_curses probe with
        # plain -lssl/-lncurses and fail or silently hit system libraries.
        AutotoolsDeps(self).generate()

        pkg = PkgConfigDeps(self)
        # Upstream asks for the pkg-config module `libargon2`, the conan
        # argon2 recipe would emit `argon2.pc` — consumer side rename via the
        # documented PkgConfigDeps API (smallest possible surface; no env var
        # duplication, no hand written .pc shim).
        pkg.set_property("argon2", "pkg_config_name", "libargon2")
        pkg.generate()

        VirtualBuildEnv(self).generate()  # gettext tool_requires -> PATH

    def build(self):
        apply_conandata_patches(self)
        # The release tarball ships a stale in-source `libyacurs/include/libyacurscfg.h`
        # (an out-of-date *generated* file from the upstream packager's machine,
        # carrying `#define ENABLE_NLS 1` while this platform's configure decides
        # NLS=no).  `curs.cc` first includes the build-tree `config.h` (NLS undef),
        # then `yacurs.h` re-includes `libyacurscfg.h` by *quote* include, which
        # resolves to the source-tree copy in its own directory and flips
        # ENABLE_NLS back to 1 — but `gettext.h` already decided at undef time not
        # to include <libintl.h>, so `bindtextdomain()` is undeclared.  The build
        # tree gets its own correct copy from config.status, so dropping the
        # stale source copy is the fix (generated + regenerated every build =>
        # no refresh_patch registration needed; E678 same-family).
        stale_cfg = os.path.join(self.source_folder, "libyacurs", "include",
                                 "libyacurscfg.h")
        if os.path.isfile(stale_cfg):
            os.remove(stale_cfg)
        self.output.info(
            "[stale-cfg] libyacurs/include/libyacurscfg.h removed: %s"
            % (not os.path.exists(stale_cfg)))
        autotools = Autotools(self)
        autotools.configure()
        # -j1: HMDFS forbids the make jobserver FIFO (device-facts §一.13/R9)
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["-j1"])
        # libtool .la wrappers embed absolute build paths — drop them.
        libdir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(libdir):
            for name in os.listdir(libdir):
                if name.endswith(".la"):
                    os.remove(os.path.join(libdir, name))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Ground truth (install runs): this package ships ONLY the three CLI
        # tools under bin/ plus share/ docs — no lib/ and no include/, because
        # the top-level configure forces `--disable-install` on the bundled
        # libyacurs (see generate()).  Claiming libs/includedirs would make
        # G4's package_info ↔ package-tree check mismatch the real tree.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin"))
        # YAPET 1.0 format files are Blowfish encrypted (cryptofactoryhelper.cc:
        # isYapet10File -> BlowfishFactory), and OpenSSL 3 moved Blowfish into
        # the legacy provider.  libcrypto.a embeds a MODULESDIR pointing at the
        # conan build folder, which is gone by consume time, so without this
        # the consumer's OSSL_PROVIDER_load("legacy") fails at run time
        # (A/B: no variable -> "Error initializing cipher"; with variable ->
        # tests green).  Repo precedent: ppp/2.5.2 package_info(), same construct.
        self.runenv_info.define_path(
            "OPENSSL_MODULES",
            os.path.join(self.dependencies["openssl"].package_folder,
                         "lib", "ossl-modules"),
        )
