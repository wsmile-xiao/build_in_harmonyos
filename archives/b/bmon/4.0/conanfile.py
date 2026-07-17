#!/usr/bin/env python3
"""Conan recipe — bmon 4.0 (autotools application).

bmon is a portable bandwidth monitor and rate estimator. On HarmonyOS PC it is
adapted as follows (see notes.md for the full rationale):

  * libconfuse (a hard, unconditional build dependency) is not published to the
    artifact repository, so its source is fetched and compiled statically into
    bmon. No external Conan dependency is required.
  * libnl/netlink is unavailable on the target, so the netlink input module is
    compiled out and bmon falls back to the /proc/net/dev (in_proc) reader.
  * ncurses is unavailable on the target, so the curses UI is disabled; bmon
    still provides its ascii/format text output modules.
"""
import os

from conan import ConanFile
from conan.tools.files import (get, save, replace_in_file, apply_conandata_patches,
                               export_conandata_patches)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


# Minimal config.h used to compile the vendored libconfuse 3.3 directly against
# a modern musl/POSIX libc, without running its own configure.
_CONFUSE_CONFIG_H = """\
#ifndef CONFUSE_CONFIG_H
#define CONFUSE_CONFIG_H
#define STDC_HEADERS 1
#define HAVE_STRING_H 1
#define HAVE_STRINGS_H 1
#define HAVE_STDLIB_H 1
#define HAVE_UNISTD_H 1
#define HAVE_SYS_STAT_H 1
#define HAVE_SYS_TYPES_H 1
#define HAVE_STDINT_H 1
#define HAVE_INTTYPES_H 1
#define HAVE_STRDUP 1
#define HAVE_STRNDUP 1
#define HAVE_STRCASECMP 1
#define HAVE_SETENV 1
#define HAVE_UNSETENV 1
#define HAVE_FMEMOPEN 1
/*
 * Intentionally NOT defining HAVE_REALLOCARRAY: some musl sysroots do not
 * declare reallocarray() under _GNU_SOURCE. Leaving it unset makes confuse.c
 * declare its own prototype and use the bundled reallocarray.c implementation
 * (compiled below), which is portable across all target musl variants.
 */
#define PACKAGE "confuse"
#define PACKAGE_NAME "libConfuse"
#define PACKAGE_VERSION "3.3"
#define PACKAGE_STRING "libConfuse 3.3"
#define VERSION "3.3"
#endif
"""


class BmonConan(ConanFile):
    name = "bmon"
    version = "4.0"
    description = "bmon - portable bandwidth monitor and rate estimator"
    license = "MIT AND BSD-2-Clause"
    homepage = "https://github.com/tgraf/bmon"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        pass  # libconfuse is vendored; no external Conan dependencies

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Vendored libconfuse source (compiled statically in build()).
        get(self, **self.conan_data["confuse"], strip_root=True,
            destination=os.path.join(self.source_folder, "confuse"))

    @property
    def _confuse_src(self):
        return os.path.join(self.source_folder, "confuse", "src")

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Disable the curses UI (no ncurses on target) and the netlink input
        # module (no libnl on target); the source patch keys off these macros.
        tc.extra_defines.append("BMON_NO_CURSES")
        tc.extra_defines.append("BMON_NO_NETLINK")
        tc.configure_args.append("--disable-curses")
        # config.guess (2015) cannot map the HarmonyOS worker's uname
        # (uname -s = HarmonyOS) -> "cannot guess build type". Pass the triplet
        # explicitly (config.sub is patched to accept -linux-ohos) so config.guess
        # is never invoked; build == host keeps this a native (non-cross) build.
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")

        env = tc.environment()
        # Feed the vendored libconfuse flags to bmon's configure so its
        # PKG_CHECK_MODULES([CONFUSE]) uses them and skips pkg-config discovery.
        env.define("CONFUSE_CFLAGS", "-I" + self._confuse_src)
        env.define("CONFUSE_LIBS", os.path.join(self._confuse_src, "libconfuse.a"))
        # libnl is compiled out; feed non-empty flags to skip its pkg-config checks.
        for var in ("LIBNL_CFLAGS", "LIBNL_LIBS", "LIBNL_ROUTE_CFLAGS", "LIBNL_ROUTE_LIBS"):
            env.define(var, " ")
        # AX_WITH_CURSES hard-requires a color curses library; pre-seed its cache.
        env.define("ax_cv_curses", "yes")
        env.define("ax_cv_curses_color", "yes")
        # pkg-config is only needed to satisfy configure's AC_PATH_PROG check.
        cc = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get("c", "")
        pkgcfg = os.path.join(os.path.dirname(cc), "pkg-config") if os.path.dirname(cc) else "pkg-config"
        env.define("PKG_CONFIG", pkgcfg)
        tc.generate(env)

    def _build_confuse(self):
        """Compile the vendored libconfuse 3.3 into a static archive."""
        cc = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get("c", "cc")
        bindir = os.path.dirname(cc)
        ar = os.path.join(bindir, "ar") if bindir else "ar"
        ranlib = os.path.join(bindir, "ranlib") if bindir else "ranlib"
        src = self._confuse_src
        save(self, os.path.join(src, "config.h"), _CONFUSE_CONFIG_H)
        cflags = "-DHAVE_CONFIG_H -D_GNU_SOURCE -O2 -I" + src
        # reallocarray.c provides the portable reallocarray() used by confuse.c
        # (see HAVE_REALLOCARRAY note above).
        units = ("confuse", "lexer", "reallocarray")
        for unit in units:
            self.run('%s %s -c %s -o %s' % (
                cc, cflags,
                os.path.join(src, unit + ".c"),
                os.path.join(src, unit + ".o")))
        objs = " ".join(os.path.join(src, u + ".o") for u in units)
        self.run('%s rcs %s %s' % (
            ar, os.path.join(src, "libconfuse.a"), objs))
        self.run('%s %s' % (ranlib, os.path.join(src, "libconfuse.a")))

    def build(self):
        apply_conandata_patches(self)
        self._build_confuse()
        # OHOS/HMDFS: files created under `umask 077` become unreadable by the
        # config.status awk substitution machinery -> "Permission denied:
        # subs1.awk" -> "could not setup config files machinery". Relax to 022.
        configure = os.path.join(self.source_folder, "configure")
        replace_in_file(self, configure, "umask 077", "umask 022", strict=False)
        autotools = Autotools(self)
        autotools.configure()
        # config.status is regenerated by configure; relax its umask too in case
        # make re-invokes it.
        cfg_status = os.path.join(self.source_folder, "config.status")
        if os.path.exists(cfg_status):
            replace_in_file(self, cfg_status, "umask 077", "umask 022", strict=False)
        # No automake/autoconf in the build image; neutralize the maintainer
        # regeneration rules so timestamp skew does not trigger a rebuild.
        no_regen = ["ACLOCAL=:", "AUTOCONF=:", "AUTOHEADER=:", "AUTOMAKE=:", "MAKEINFO=:"]
        autotools.make(args=no_regen)

    def package(self):
        autotools = Autotools(self)
        no_regen = ["ACLOCAL=:", "AUTOCONF=:", "AUTOHEADER=:", "AUTOMAKE=:", "MAKEINFO=:"]
        autotools.install(args=no_regen)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
