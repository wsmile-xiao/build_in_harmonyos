#!/usr/bin/env python3
"""Conan recipe for libaudclient 3.5-rc2.1 (packaging revision .1 of upstream 3.5-rc2) on HarmonyOS PC (aarch64, OHOS).

Key platform decisions (see notes.md for evidence):
  * Source is the official distfiles tarball, not the GitHub tag archive:
    only the release tarball ships the pre-generated `configure` and the
    pre-generated `dbus-client-bindings.h`, so no autoconf/automake run is
    needed on device (CI matrix has no autotools guarantee).
  * Upstream audacious buildsys hardcodes the shared object only
    (SHARED_LIB in src/libaudclient/Makefile); no static option exists,
    so the recipe declares no shared/fPIC options.
  * OHOS dependency variants differ per package: dbus/dbus-glib ship
    static archives (dbus-glib with fPIC=True) while glib/2.84.0.1
    publishes only a shared=True binary (libglib-2.0.so + soname copies
    + libintl.so, no .a at all) and expat ships a shared object. The
    E236 la-free directory therefore mirrors the static archives only;
    the shared dependencies are referenced through their own package lib
    directories, and build() rebuilds the directory from
    self.dependencies on every run (never from a conan cache path, never
    mutating the cache). The upstream Makefile appends ${GLIB_LIBS}
    before ${DBUS_LIBS}; libdbus-glib-1.a is the glib consumer and GNU
    ld resolves archives left to right, so
    0003-makefile-link-order.patch swaps the append order and both
    preset variables carry non-empty dependency-ordered link lines.
    Only the glib shared objects are named on the GLIB_LIBS line:
    libffi/pcre2/zlib are static and already embedded inside
    libglib-2.0.so, so listing them would search for archives that can
    close no remaining undefined symbol (-lffi would fail outright).
  * configure runs a second, separate `glib-2.0 >= 2.28` module check;
    pkg.m4's preset detection is `test -n "$VAR"`, so GLIB_LIBS must be
    non-empty too or configure falls through to a pkg-config query and
    aborts.
  * configure hard-requires dbus-binding-tool (AC_PATH_PROG + error);
    the published dbus-glib/0.114.1 package ships it in bin/ and the
    recipe pins DBUS_BINDING_TOOL to that absolute path (host == build
    for native conan create on the OHOS device).
  * PKG_CHECK_MODULES is skipped by presetting DBUS_CFLAGS/DBUS_LIBS
    (pkg.m4 honors preset variables), avoiding dbus-1.pc/dbus-glib-1.pc
    alias generation entirely (same approach as dbus-glib 0.114).
"""
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.build import load_toolchain_args
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain


class LibaudclientConan(ConanFile):
    name = "libaudclient"
    version = "3.5-rc2.1"
    description = (
        "Audacious D-Bus client library: audctrl remote-control API "
        "plus audclient.pc for driving a running Audacious player."
    )
    license = "BSD-2-Clause"
    homepage = "https://www.audacious-media-player.org/"
    url = "https://github.com/audacious-media-player/libaudclient"

    # Upstream buildsys produces only SHARED_LIB (no STATIC_LIB target in
    # src/libaudclient/Makefile), so the honest declaration is a
    # shared-library package; declaring generic "library" makes Conan 2
    # demand a shared option whose False branch upstream cannot build.
    package_type = "shared-library"
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        # Version alignment (single graph ⇒ single glib; R36):
        #   The GTK+2 stack in this repository pins glib/2.84.0.1
        #   (gtk2/2.24.33, pango/1.50.14.1.1, atk/2.38.0.1,
        #   gdk-pixbuf/2.44.6.1). dbus-glib/0.114 pulls glib/2.88.0,
        #   which cannot coexist with it in one graph, so pin
        #   dbus-glib/0.114.1 — its graph resolves glib/2.84.Z. With this
        #   package also pinned to glib/2.84.0.1 its package_id matches
        #   the one the wmauda/0.9 consumer graph (glib override →
        #   2.84.0.1) asks for, so the published registry binary is
        #   reused instead of silently rebuilt from source.
        # Direct link/header inputs (all published to the OHOS registry):
        #   dbus-glib: dbus/dbus-glib.h + libdbus-glib-1.a
        #   dbus:      dbus/dbus.h (via dbus/dbus-glib.h) + libdbus-1.a
        #   glib:      glib.h via dbus/dbus-glib.h; libaudclient.so links
        #              the published glib/2.84.0.1 shared binary
        #              (DT_NEEDED libglib-2.0.so.0), so consumers need its
        #              include dirs pinned at the component level (E216).
        #              transitive_headers=True is REQUIRED: Conan marks the
        #              deps of a shared-library package headers=False for
        #              downstream consumers, which makes PkgConfigDeps
        #              drop glib from the generated .pc Requires chain and
        #              consumer compiles of audctrl.h fail with
        #              "'glib.h' file not found".
        # expat/pcre2/zlib stay transitive: no consumer-visible headers,
        # and expat's .so reaches the runtime env through the graph.
        self.requires("dbus-glib/0.114.1")
        self.requires("dbus/1.14.10")
        self.requires("glib/2.84.0.1", transitive_headers=True)

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # audacious buildsys is in-source only: the checked-in top-level
        # Makefile includes the generated buildsys.mk, and buildsys.mk.in
        # has no VPATH support, so make must run where configure wrote it.
        self.folders.source = "."
        self.folders.build = "."
        self.folders.generators = "conan"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _dep_pkg(self, dep):
        return self.dependencies[dep].package_folder

    @property
    def _la_free_dir(self):
        return os.path.join(self.build_folder, "dependency-archives")

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

        glib = self._dep_pkg("glib")
        dbglib = self._dep_pkg("dbus-glib")
        dbus = self._dep_pkg("dbus")
        expat = self._dep_pkg("expat")
        la = self._la_free_dir

        # E236: configure resolves everything through dependency-scoped
        # cache variables; the static archives come from the la-free
        # directory assembled in build(), while the SHARED dependencies
        # (glib/2.84.0.1, expat) are referenced through their own package
        # lib directories. Those carry no .la metadata, and mirroring them
        # would have to reproduce the soname symlink chain
        # (libexpat.so -> libexpat.so.1 -> libexpat.so.1.12.2), which
        # cannot be assumed to survive every filesystem. No pkg-config
        # file aliases are needed.
        env = Environment()
        # Preset variables make PKG_CHECK_MODULES skip pkg-config (pkg.m4
        # honors preset _CFLAGS/_LIBS), so the dbus-1/dbus-glib-1 checks
        # and the separate `glib-2.0 >= 2.28` check never run.
        env.define("DBUS_CFLAGS",
                   f"-I{os.path.join(dbglib, 'include', 'dbus-1.0')} "
                   f"-I{os.path.join(dbus, 'include', 'dbus-1.0')} "
                   f"-I{os.path.join(dbglib, 'include')} "
                   f"-I{os.path.join(dbus, 'include')}")
        # Dependency-ordered static link lines split across the two
        # variables the Makefile appends. 0003 swaps the append order to
        # `${DBUS_LIBS} ${GLIB_LIBS}`: libdbus-glib-1.a is the glib
        # consumer, and GNU ld resolves archives left to right, so it must
        # precede the glib libraries. Both values must be NON-EMPTY: pkg.m4
        # presets via `test -n "$VAR"`, and an empty string falls through
        # to a pkg-config query that aborts configure.
        env.define("DBUS_LIBS",
                   f"-L{la} -L{os.path.join(expat, 'lib')} "
                   "-ldbus-glib-1 -ldbus-1 -lexpat")
        env.define("GLIB_CFLAGS",
                   f"-I{os.path.join(glib, 'include', 'glib-2.0')} "
                   f"-I{os.path.join(glib, 'lib', 'glib-2.0', 'include')}")
        # Only the glib shared objects are named here. libffi/pcre2/zlib
        # are static and already embedded inside libglib-2.0.so, so
        # listing them would look for archives that close no remaining
        # undefined symbol — and -lffi fails outright (libffi is not part
        # of this link line). -lintl is kept: glib/2.84.0.1 ships a real
        # libintl.so while the OHOS sysroot libintl.h is an empty stub
        # (gdk-pixbuf/2.44.6.1 precedent).
        env.define(
            "GLIB_LIBS",
            f"-L{la} -L{os.path.join(glib, 'lib')} "
            "-lgio-2.0 -lgobject-2.0 -lgthread-2.0 -lgmodule-2.0 "
            "-lglib-2.0 -lintl")
        # configure aborts without it (AC_PATH_PROG + AC_MSG_ERROR); the
        # arm64 binary from the published dbus-glib package runs natively
        # on the device where conan create executes (host == build).
        env.define("DBUS_BINDING_TOOL",
                   os.path.join(dbglib, "bin", "dbus-binding-tool"))
        # HMDFS timestamp granularity can trigger autotools re-maintenance
        # rules; this buildsys has no automake regeneration, but neutralize
        # the wrapper tools anyway (dbus-glib 0.114 precedent, CI-proven).
        if str(self.settings.os) == "OHOS":
            env.define("ACLOCAL", "true")
            env.define("AUTOMAKE", "true")
            env.define("AUTOCONF", "true")
        env.vars(self, scope="build").save_script("libaudclient-deps")

    def build(self):
        apply_conandata_patches(self)

        # E236: mirror the dependency STATIC archives into a build-private,
        # .la-free directory, rebuilt from self.dependencies on every run —
        # no conan cache path is ever read (the CI worker's CONAN_HOME is
        # ~/.conan2) and the cache itself is never mutated. The static
        # dependencies here are libdbus-glib-1.a / libdbus-1.a (dbus-glib
        # is built with fPIC=True, so the archives can be linked into a
        # shared object).
        # Shared dependencies (glib/2.84.0.1, expat) are deliberately NOT
        # mirrored: they are referenced through their own package lib
        # directories from generate(), and expat's libexpat.so is a
        # symlink chain that a flat copy cannot faithfully reproduce.
        la = self._la_free_dir
        os.makedirs(la, exist_ok=True)
        for _, dep in self.dependencies.host.items():
            if not dep.package_folder:
                continue
            libdir = os.path.join(dep.package_folder, "lib")
            if not os.path.isdir(libdir):
                continue
            copy(self, "*.a", src=libdir, dst=la, keep_path=False)
        self.output.info(f"la-free archives: {sorted(os.listdir(la))}")

        # Upstream test-suite audit: libaudclient ships no automated tests.
        # Keep the machine-checkable evidence in the conan create log.
        self.run(
            "echo 'upstream test audit:'; "
            "find . -path ./dependency-archives -prune -o -name tests -print; "
            "grep -rnE '(^|[^A-Za-z_])TESTS|check_PROGRAMS|check-local' "
            "Makefile src/*/Makefile buildsys.mk.in configure.ac || "
            "echo 'no TESTS/check_PROGRAMS/check-local/check target in any "
            "Makefile or configure.ac'",
            cwd=self.source_folder)

        autotools = Autotools(self)
        # This configure is autoconf 2.69-generated: with CONFIG_SHELL set
        # (the CI profile points it at hnp bash 5.3) it unconditionally
        # re-execs itself under that shell. That bash fails its startup
        # getcwd on HMDFS whenever the inherited PWD is stale, and the
        # ac_pwd probe then aborts with "working directory cannot be
        # determined" (toybox /bin/sh is unaffected). CONFIG_SHELL must be
        # unset, not merely emptied: configure's preamble assigns
        # SHELL=${CONFIG_SHELL-/bin/sh}, which does not fall back on an
        # empty-but-set value, and that empty SHELL is AC_SUBSTed into
        # buildsys.mk where GNU make then fails recipes with
        # "make: -c: No such file or directory" (it execs "-c" directly).
        toolchain_args = load_toolchain_args(self.generators_folder)
        self.run(
            f'unset CONFIG_SHELL; '
            f'"{os.path.join(self.source_folder, "configure")}" '
            f'{toolchain_args.get("configure_args")}',
            cwd=self.build_folder, env="conanbuild")
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "audclient")
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["audclient"]
        # Component-level pins restricted to DIRECT requirements (Conan 2
        # rejects transitive component refs); expat/pcre2/zlib propagate
        # through dbus-glib/dbus in the consumer graph.
        self.cpp_info.requires = [
            "dbus-glib::dbus-glib",
            "dbus::dbus",
            "glib::glib-2.0",
            "glib::gobject-2.0",
            "glib::gthread-2.0",
            "glib::gmodule-2.0",
            "glib::gio-2.0",
        ]
