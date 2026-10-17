#!/usr/bin/env python3
"""Conan recipe for shush 1.2.3 (HarmonyOS PC, aarch64-linux-ohos).

shush runs a command (typically a cron job), analyses its standard output and
standard error with POSIX or Perl compatible (PCRE2) regular expressions and
mails reports through a sendmail(1) compatible program.

Build system: autotools (Autoconf 2.59 configure, hand-written Makefile.in,
built in-source; upstream "make install" ignores DESTDIR).

HarmonyOS PC adaptation points (details and evidence in notes.md):
  - patches 0001/0002: the 2004 config.guess/config.sub know neither aarch64
    nor HarmonyOS (`uname -s` = HarmonyOS); taught both (E007).
  - patches 0004/0003/0009 + 0006/0011: PCRE (end of life) ported to PCRE2.
    The C hunks come from Debian's 03_port_to_pcre2.diff (Bug #999964) plus
    two fixes; configure/config.h.in are the output of the original
    Autoconf 2.59 for the patched configure.ac (autoconf is not a build
    requirement: the OHOS autoconf package needs OHOS perl/m4).
  - patch 0003 also creates the config.status scratch directory with
    mkdir under umask 000 (HMDFS UID projection, E011).
  - patch 0005: signals.h used to be generated from the build host's
    /usr/include, which gives an empty table (timeout=...,SIGTERM rejected);
    it now comes from the target compiler's <signal.h>.
  - patches 0007/0010: shush refuses configuration files owned by another
    uid or group writable.  HMDFS projects file ownership onto a shared
    identity and forces the group write bit, so with
    --enable-relaxed-ownership only world writable files are refused.
  - patches 0008/0012: missing <time.h>/<sys/types.h> (musl, clang 15).
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, load
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class ShushConan(ConanFile):
    name = "shush"
    version = "1.2.3"
    description = "Run a command (e.g. a cron job) and optionally report its output by mail"
    # LICENSE keeps the advertising clause (4 clauses).
    license = "BSD-4-Clause"
    homepage = "https://web.taranis.org/shush/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("cron", "mail", "monitoring", "pcre2", "cli")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: OHOS must be accepted alongside Linux, never "== Linux".
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"shush supports Linux and OHOS only, got {self.settings.os}")
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("shush on OHOS supports armv8 only")

    def requirements(self):
        # Static libpcre2-8.a: linked into the executable, nothing at run time.
        self.requires("pcre2/10.45")

    def layout(self):
        basic_layout(self)
        # Makefile.in/src/Makefile.in are not VPATH aware: build in-source.
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Upstream's own --with-pcre=DIR adds DIR/include and DIR/lib; only
        # -lpcre2-8 is linked (the package also ships an unused pcre2-posix).
        pcre2 = self.dependencies["pcre2"].package_folder
        tc.configure_args.append(f"--with-pcre={pcre2}")
        # AC_PATH_PROG would bake the build machine's sendmail/crontab paths
        # into the binary (an x86 runner has /usr/sbin/sendmail and
        # /usr/bin/crontab, HarmonyOS has neither).  Pin the values configure
        # finds on the target itself; sendmail is set at run time through the
        # "sendmail" parameter or SHUSH_SENDMAIL.
        tc.configure_args.append("ac_cv_path_SENDMAIL=NOSENDMAIL")
        tc.configure_args.append("ac_cv_path_CRONTAB=NOCRONTAB")
        if str(self.settings.os) == "OHOS":
            # Conan does not inject a triplet because the build and host
            # profiles are both OHOS.  --host without --build selects
            # autoconf's cross_compiling=maybe: native run checks on an
            # aarch64 builder, cross mode on an x86_64 one.  The build
            # triplet comes from the patched config.guess.
            tc.configure_args.append("--host=aarch64-linux-ohos")
            tc.configure_args.append("--enable-relaxed-ownership")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        config_h = load(self, os.path.join(self.build_folder, "src", "config.h"))
        if "#define HAVE_PCRE_H 1" not in config_h:
            raise ConanException(
                "configure did not enable PCRE2 support, see config.log")
        # -j1: no GNU make jobserver FIFO (HMDFS has no mkfifo, E074).
        autotools.make(args=["-j1"])

    def package(self):
        # Upstream "make install" ignores DESTDIR and would write to the
        # build machine's ${prefix}: copy the two installed files instead.
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "shush", src=os.path.join(self.build_folder, "src"),
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "shush.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
