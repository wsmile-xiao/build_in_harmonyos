#!/usr/bin/env python3
"""Conan recipe — tta 2.2 (Autotools). True Audio (TTA) lossless audio codec.

Builds libtta.a (the codec library) and console/tta (a command line
encoder/decoder) with the upstream Autotools build. Adapted for HarmonyOS
PC (aarch64): the bundled 2005 config.sub does not recognise aarch64 and
the generated configure CPU guard rejects an unknown host_cpu, so both
config.sub and the configure script are patched to map aarch64 to the ARM
code path. configure.ac is intentionally NOT patched (touching it triggers
automake maintainer-mode regeneration of aclocal.m4, which fails when no
autotools are present).

Upstream tta 2.2 ships no formal automated-test framework: Makefile.am
defines no TESTS/check_PROGRAMS and the tarball contains no test source or
test directory (make check runs 0 tests). It DOES ship the console/tta
command-line encode/decode tool, which test_package promotes into an
upstream regression suite (encode/decode/bit-exact roundtrip); the consumer
also exercises the installed libtta.a library with encode->decode.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class TtaConan(ConanFile):
    name = "tta"
    version = "2.2"
    description = "The True Audio (TTA) lossless audio codec library (ANSI-C) with a command-line encoder/decoder"
    license = "LGPL-3.0"
    homepage = "http://www.true-audio.com/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "static-library"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os check must use in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"tta is supported only on Linux/OHOS, got {self.settings.os}"
            )
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                "OHOS builds of tta require aarch64 (armv8) because the ARM "
                "code path is the only one patched for aarch64"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Upstream is a plain automake static library (no libtool), so it
        # offers no --enable-static/--disable-shared options. It only ever
        # produces libtta.a, so we do not add unsupported configure flags.
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # OHOS HMDFS: autoconf re-executes `configure` with the toolchain
        # $CONFIG_SHELL (/data/service/hnp/bin/bash), whose getcwd(2) fails on
        # the HMDFS build dir ("shell-init: error retrieving current directory"
        # / "configure: error: working directory cannot be determined").
        # `/bin/sh` (mksh) works on HMDFS, so pin CONFIG_SHELL/SHELL to it inline
        # (an inline assignment wins over any profile [buildenv] export, and it is
        # recorded into config.status so config.status/make also use /bin/sh).
        autotools = Autotools(self)
        # AutotoolsToolchain-generated configure flags (--prefix, --bindir,
        # --disable-shared/--enable-static, build/host triplets, ...) come from
        # _configure_args; Autotools.configure() builds its command from the same.
        extra = ""
        if str(self.settings.os) == "OHOS":
            # build/host profiles are both OHOS aarch64, so Conan's AutotoolsToolchain
            # does not treat this as cross-building and emits no --build/--host. The
            # bundled 2005 config.guess cannot guess "HarmonyOS", so autoconf aborts
            # with "cannot guess build type; you must specify one". Supply the triplet
            # explicitly (aarch64-linux-ohos; matches the config.sub patch in 0001).
            extra = " --build=aarch64-linux-ohos --host=aarch64-linux-ohos"
        # HMBS platform diagnosis [unsafe_local_mktemp]: on this device
        # filesystem a dir produced by `mktemp` cannot be written by Autoconf
        # afterwards, and even the AS_TMPDIR `mkdir` fallback stays unusable
        # as long as it keeps `umask 077`: on HMDFS the setgid + 077 dir comes
        # out owner-unwritable, so config.status dies in "./conf*/subs1.awk:
        # Permission denied" -> "could not setup config files machinery".
        # zzuf/liblzf precedent: relax the generated script's umask 077 -> 022
        # so the ./conf* temp dir is writable. Patch 0003 therefore drops the
        # mktemp branch of autoconf's AS_TMPDIR, always uses the `mkdir` path
        # and builds it under `umask 022`. We also run configure/make under an
        # explicit `umask 022` so the build dir and all generated temp dirs
        # carry group/other read-exec (no runtime mktemp shim on PATH is
        # needed; a PATH shim would itself require chmod, which HMBS reports as
        # unsupported here: HMBS_CAP_CHMOD=0). configure still runs under
        # $CONFIG_SHELL=/bin/sh and config.status inherits ac_tmp, so the fixed
        # point survives into config.status.
        configure_cmd = 'umask 022 && CONFIG_SHELL=/bin/sh SHELL=/bin/sh "{}/configure" {}{}'.format(
            self.source_folder, autotools._configure_args or "", extra)
        self.run(configure_cmd)
        # make runs under the process umask; the baked-in `umask 022` in the
        # patched configure/config.status guarantees the ./conf* temp dir is
        # writable, and no ./conf* dirs are created during compilation.
        autotools.make(args=["SHELL=/bin/sh", "-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Upstream declares libtta.h only as a library source, not via
        # include_HEADERS, so make install does not ship it. Copy the public
        # header into the package include dir so consumers can #include it.
        copy(self, "libtta.h",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["tta"]
        self.cpp_info.bindirs = ["bin"]
