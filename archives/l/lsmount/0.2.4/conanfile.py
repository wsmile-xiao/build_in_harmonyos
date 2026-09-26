#!/usr/bin/env python3
"""Conan recipe for lsmount 0.2.4 — /proc/mounts pretty-printer.

Upstream build system is a hand-written Makefile with **no configure script**,
**no PREFIX/DESTDIR/INSTALL handle**, and an ``install`` target that copies
straight into ``/usr/bin``, ``/etc`` and ``/usr/share/man`` (and additionally
requires the host-only ``a2x``/asciidoc toolchain for the manpage).

Everything the Makefile burns in is therefore redirected from the *make command
line* and the *environment* instead of patching, except one genuine
null-pointer defect that OHOS exposes (see patches/ and notes.md).

Key overrides used here (all of them are upstream handles, no source edits):
  * ``CC``            — Makefile line 3 burns ``/usr/bin/gcc``; simple ``=`` so
                        only a command-line assignment wins. Taken from Conan
                        conf (R33), never from a bare shell ``$CC``.
  * ``LDFLAGS``       — Makefile line 8 burns ``-ltermcap -z now``; simple ``=``,
                        so the environment is ignored and the value must be
                        restated on the command line. ``-ltermcap`` does not
                        exist for OHOS: ``ncurses/6.5`` publishes only
                        ``libncursesw.a``, which is where ``setupterm``,
                        ``tigetnum`` and ``del_curterm`` live. ``-z now`` is
                        carried over verbatim so upstream's BIND_NOW hardening
                        is preserved.
  * ``CFLAGS``        — Makefile lines 5/6/13 use ``+=``, so an *environment*
                        CFLAGS is kept and appended to (a command-line CFLAGS
                        would silently drop upstream's ``-std=gnu99``,
                        ``-D_GNU_SOURCE``, ``-fcommon`` and the hardening set in
                        line 13 — that trap is why this goes through the
                        toolchain environment instead).
  * ``make install``  — never invoked; ``package()`` stages the binary itself.
"""
import os

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.gnu import AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout

# OHOS' sysroot ships a 353-byte ``libintl.h`` stub that declares *nothing*:
# no ``gettext``, no ``textdomain``, no ``bindtextdomain``. Upstream maps its
# ``_()`` macro onto a bare ``gettext()`` call, so the implicit declaration
# turns into ``-Wint-conversion`` errors under clang. lsmount ships no
# translation catalogue at all (no po/, no *.mo), so NLS is inert and the
# behaviour-preserving equivalent of E027's ``--disable-nls`` is to map the
# three entry points to identity/no-op at compile time.
#
# The single quotes are load-bearing: the Makefile expands $(CFLAGS) unquoted
# into the recipe line, so the shell that runs the recipe must be the one that
# strips them (otherwise ``(`` is a syntax error in /bin/sh).
_NLS_DISABLED_CFLAGS = [
    "-D'gettext(x)=(x)'",
    "-D'textdomain(x)=((void)0)'",
    "-D'bindtextdomain(d,p)=((void)0)'",
]


class LsmountConan(ConanFile):
    name = "lsmount"
    version = "0.2.4"
    description = ("lsmount — formats the /proc/mounts table as an aligned, "
                   "optionally coloured terminal grid")
    license = "ISC"
    homepage = "https://www.lsmount.org"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Both pinned to the exact published revisions verified in W0.
        self.requires("libconfig/1.7.3")
        self.requires("ncurses/6.5")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _dep_paths(self, pkg):
        """Absolute include/lib dirs of a requirement (cpp_info dirs are
        relative to package_folder in Conan 2)."""
        dep = self.dependencies[pkg]
        info = dep.cpp_info.aggregated_components()
        root = dep.package_folder
        return ([os.path.join(root, d) for d in info.includedirs if d],
                [os.path.join(root, d) for d in info.libdirs if d])

    def generate(self):
        # Upstream's Makefile asks pkg-config for libconfig itself. The .pc that
        # ships inside the published libconfig package is *not relocatable*
        # (``prefix=/`` → ``-I/include -L/lib``), so Conan's generated .pc plus
        # VirtualBuildEnv's PKG_CONFIG_PATH is what makes that call resolve to
        # the Conan dependency instead of a nonexistent system prefix.
        VirtualBuildEnv(self).generate()
        PkgConfigDeps(self).generate()

        ncurses_inc, _ = self._dep_paths("ncurses")

        tc = AutotoolsToolchain(self)
        # NOTE: AutotoolsToolchain.cflags is a read-only *property* computed from
        # extra_cflags — appending to tc.cflags silently disappears (observed on
        # A 机: only "-O3" reached the compiler and gettext came back undeclared).
        # curses.h / term.h: upstream never asks pkg-config for these, and there
        # is no INCS/CPPFLAGS handle in the Makefile to override.
        tc.extra_cflags.extend(f"-I{d}" for d in ncurses_inc)
        tc.extra_cflags.extend(_NLS_DISABLED_CFLAGS)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # R33: compiler comes from the Conan conf, never from shell $CC.
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = (compilers or {}).get("c", "clang")

        # Link line = Makefile line 20 `$(CC) -o $@ $(OBJ) $(LDLIBS) $(LDFLAGS)`.
        # LDFLAGS replaces `-ltermcap -z now` entirely, so `-z now` is restated
        # and both dependency lib dirs are spelled out (independent of whether
        # the pkg-config call inside LDLIBS resolves).
        _, ncurses_lib = self._dep_paths("ncurses")
        _, libconfig_lib = self._dep_paths("libconfig")
        ldflags = " ".join(
            [f"-L{d}" for d in ncurses_lib + libconfig_lib]
            + ["-lncursesw",   # setupterm / tigetnum / del_curterm / cur_term
               "-lconfig",     # config_init / config_read_file / ...
               "-z now"])      # upstream hardening, preserved from line 8

        # R9: -j1. `all` is the default target and does NOT depend on `manpage`,
        # so the absent host-side asciidoc/xmlto toolchain is never reached.
        self.run(f'make CC="{cc}" LDFLAGS="{ldflags}" -j1',
                 cwd=self.source_folder, env="conanbuild")

    def package(self):
        # `make install` is unusable (burned /usr/bin + /etc + /usr/share/man and
        # it depends on the a2x manpage target), so staging is done here.
        copy(self, "lsmount", self.source_folder,
             os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)
        # Upstream ships its default configuration and the manpage *source*
        # (doc/lsmount.txt). The rendered lsmount.1.gz cannot be produced on the
        # OHOS build host (needs a2x + xmlto), so the plain-text source is kept
        # verbatim rather than faking a rendered page.
        copy(self, "lsmount.rc.default", os.path.join(self.source_folder, "share"),
             os.path.join(self.package_folder, "res"), keep_path=False)
        copy(self, "lsmount.txt", os.path.join(self.source_folder, "doc"),
             os.path.join(self.package_folder, "res"), keep_path=False)

    def package_info(self):
        # Application package: consumers run the binary, they do not link it.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["res"]
        # R26 / SKILL §7: both requirements are consumed as static archives only
        # (libconfig.a, libncursesw.a), so the delivered ELF has no Conan .so
        # dependencies to resolve at runtime.
