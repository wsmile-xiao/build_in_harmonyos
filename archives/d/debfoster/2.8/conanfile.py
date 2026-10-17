#!/usr/bin/env python3
"""Conan recipe for debfoster 2.8 — keep only the packages you really need.

debfoster reads the dpkg status database, works out which installed packages
are no longer required by anything the administrator asked for, and maintains
an explicit "keeper" list of the packages that were requested on purpose.  It
is a single self-contained C program (10 .c files plus its own AVL tree and
Debian version comparison implementation) built with autotools; the only
external library is the Boehm-Demers-Weiser conservative garbage collector
(``gc``), whose ``GC_malloc``/``GC_strdup`` back every allocation in
``src/error.c``.

Upstream release tarball notes (all handled below):

* ``Makefile.am`` has a ``dist-hook`` that deletes ``config.guess``,
  ``config.sub``, ``install-sh``, ``missing``, ``depcomp`` and ``aclocal.m4``
  from the distributed tarball, while keeping the generated ``configure`` and
  ``Makefile.in``.  Debian rebuilds them with ``dh_autoreconf``; the missing
  helper files are therefore restored from GNU automake (see ``generated/``),
  with ``config.guess`` taught the HarmonyOS triplet.
* ``etc/Makefile.am`` hard-codes the coreutils ``install`` command, which does
  not exist on OHOS.
* ``src/keepers.c`` relies on glibc pulling in ``<fcntl.h>`` transitively.
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class DebfosterConan(ConanFile):
    name = "debfoster"
    version = "2.8"
    description = ("Keep only the packages you need: maintain an explicit "
                   "keeper list and prune packages that nothing depends on")
    license = "GPL-2.0-only AND LGPL-2.0-only AND LGPL-2.1-only"
    homepage = "https://salsa.debian.org/debian/debfoster"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("deb", "dpkg", "package-management", "orphan", "system-administration")

    # Upstream builds one executable (sbin_PROGRAMS) and no library.
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # Helper files deleted by the upstream dist-hook, restored verbatim from
    # GNU automake 1.18.1 except for config.guess, which is taught the
    # HarmonyOS triplet.  See generated/PROVENANCE.md for the checksums.
    _RESTORED_FILES = ("config.guess", "config.sub", "install-sh", "missing",
                       "depcomp", "aclocal.m4")

    def export_sources(self):
        export_conandata_patches(self)
        for name in self._RESTORED_FILES:
            copy(self, name, os.path.join(self.recipe_folder, "generated"),
                 os.path.join(self.export_sources_folder, "generated"))

    def requirements(self):
        # configure.ac: AC_CHECK_LIB(gc, GC_malloc); src/error.c includes
        # <gc/gc.h>.  The collector is a hard requirement, not optional.
        self.requires("gc/8.2.12")

    def layout(self):
        basic_layout(self)
        # debfoster is declared sbin_PROGRAMS upstream.  Conan's
        # AutotoolsToolchain derives both --bindir and --sbindir from
        # cpp.package.bindirs, so the executable is installed into bin/:
        # OHOS packages have no separate sbin/, and bin/ is what VirtualRunEnv,
        # the W3 L2 smoke test and downstream consumers look at.
        self.cpp.package.bindirs = ["bin"]

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Restore the autotools helper files the upstream dist-hook strips from
        # the release tarball (see generated/PROVENANCE.md).
        for name in self._RESTORED_FILES:
            copy(self, name, os.path.join(self.export_sources_folder, "generated"),
                 self.source_folder)

    def generate(self):
        # The repository passes the same profile as -pr:h and -pr:b, so
        # cross_building() is False and AutotoolsToolchain injects neither
        # --host nor --build: configure runs the HarmonyOS-aware config.guess
        # shipped in generated/ itself and reports
        # build == host == aarch64-unknown-linux-ohos.
        AutotoolsToolchain(self).generate()
        # AutotoolsToolchain only carries the compiler and its own flags; the
        # flags of the requirements (here: -I<gc>/include, -L<gc>/lib) come
        # from AutotoolsDeps.  Without it the build stops at
        # "fatal error: 'gc/gc.h' file not found".
        AutotoolsDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        self._pin_autotools_timestamps()

        autotools = Autotools(self)
        autotools.configure()
        # Shared HarmonyOS workstation: stay at one compilation job.
        autotools.make(args=["-j1"])
        # Upstream test entry point.  debfoster ships no test suite (no TESTS
        # variable in any Makefile.am, no tests directory), so every level this
        # recursion reaches has nothing to do: src enters and leaves silently,
        # etc/doc/po each print "Nothing to be done for 'check'.", and the top
        # level prints "Nothing to be done for 'check-am'."  Running it anyway
        # keeps that fact verifiable in every build log instead of asserting it
        # in prose.  See test_package/MANIFEST.yml for the counting commands.
        autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        # debfoster is GPL-2; the bundled AVL tree is LGPL-2 (Michael H.
        # Buselli) and src/symbol.* is LGPL-2.1 (Wessel Dankers).
        copy(self, "LICENSE.*", os.path.join(self.source_folder, "doc"),
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # CLI tool: no library is shipped, only bin/debfoster plus its
        # configuration file and manual page.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]

    def _pin_autotools_timestamps(self):
        """Give every autotools input and product one identical mtime.

        The release tarball ships the generated ``configure``/``Makefile.in``
        but not ``aclocal.m4`` (restored as a documented placeholder, see
        generated/aclocal.m4).  The automake maintainer rules would otherwise
        try to re-run aclocal/automake/autoconf through ``missing``, none of
        which exist on the device or on the CI worker, and abort with
        ``aclocal-1.16: inaccessible or not found`` (exit 127).  GNU make
        treats equal mtimes as up to date, so pinning the whole chain to a
        single timestamp keeps the shipped ``configure`` untouched.
        """
        stamp = 978307200  # 2001-01-01, older than every real input
        suffixes = (".m4", ".am", ".in", ".ac")
        exact = ("configure", "config.guess", "config.sub", "ltmain.sh",
                 "compile", "depcomp", "missing", "install-sh",
                 "mkinstalldirs", "aclocal.m4", "config.h.in")
        for root, _dirs, files in os.walk(self.source_folder):
            for name in files:
                if name.endswith(suffixes) or name in exact:
                    os.utime(os.path.join(root, name), (stamp, stamp))
