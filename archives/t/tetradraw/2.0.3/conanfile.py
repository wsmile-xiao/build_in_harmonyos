#!/usr/bin/env python3
"""Conan recipe for tetradraw 2.0.3 — ANSI art editor for *nix (ncursesw TUI).

Upstream ships a classic autotools layout (configure.in + pre-generated
Makefile.in/configure from autoconf 2.57).  Upstream ships no test
suite; the recipe applies 6 portability patches and verifies the
tetradraw/tetraview binaries are aarch64 ELF and actually execute
(self.run in the test_package) as the real test.

configure/make are invoked as `env -u CONFIG_SHELL SHELL=/bin/sh ...`
instead of through Autotools helpers: the shared OHOS profile exports
CONFIG_SHELL=/data/service/hnp/bin/bash and autoconf re-execs itself into
that shell, which cannot getcwd() on the HMDFS build tree (see build()).
They do run with `env="conanbuild"`, so the compiler and flags come from
AutotoolsToolchain rather than from the ambient PATH (R33), and on the
native OHOS build the triplets are pinned explicitly because the tarball's
2003-era config.guess cannot identify HarmonyOS (see _autotools_toolchain()).
"""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import (
    get, copy, apply_conandata_patches, export_conandata_patches,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class TetradrawConan(ConanFile):
    name = "tetradraw"
    version = "2.0.3"
    description = "Fully featured ANSI art editor and viewer (ncursesw TUI)"
    license = "GPL-2.0-only"
    homepage = "http://tetradraw.sourceforge.net/"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    generators = "VirtualBuildEnv", "PkgConfigDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name} only supports Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        self.requires("ncurses/6.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def _autotools_toolchain(self):
        """Single source of truth for the configure arguments.

        Both generate() and build() need the exact same list, and build()
        cannot reuse generate()'s instance (its configure_args were mutated
        there only), so the ncurses flags are re-applied from the dependency
        folder instead of being silently dropped.
        """
        tc = AutotoolsToolchain(self)
        ncpkg = self.dependencies["ncurses"].package_folder
        tc.configure_args.append(f"CPPFLAGS=-I{ncpkg}/include")
        tc.configure_args.append(f"LDFLAGS=-L{ncpkg}/lib")
        # AutotoolsToolchain only emits --host/--build when conan classifies the
        # build as a *cross* build, and CI gives both contexts the same OHOS
        # profile (the worker is itself the HarmonyOS PC).  In that native case
        # configure falls back to the tarball's config.guess, which is autoconf
        # 2.57 (2003): it cannot identify `uname -s` = HarmonyOS and dies while
        # writing its probe file into the worker's read-only temp dir ->
        #   config.guess: unable to guess system type
        #   configure: error: cannot guess build type; you must specify one
        # (CI #80123; same root cause family as #70913/#71162).  Pin the
        # triplets explicitly so config.guess is never invoked - wmtop/0.85
        # precedent - and rely on patch 0001, which teaches the old config.sub
        # the `aarch64` and `linux-ohos` spellings it needs to canonicalize
        # them.  Cross builds keep the toolchain's own triplets untouched.
        if str(self.settings.os) == "OHOS" and not cross_building(self):
            tc.configure_args.append("--build=aarch64-linux-ohos")
            tc.configure_args.append("--host=aarch64-linux-ohos")
        return tc

    def generate(self):
        self._autotools_toolchain().generate()

    # autoconf 2.57 / automake 1.4 byproduct timestamps otherwise trigger
    # phony rebuild rules that invoke `automake-1.4`, which does not exist
    # on OHOS or in CI (Error 127).  Keep every file older than its
    # (patched) prerequisites, in dependency order.
    def _fix_timestamps(self):
        here = self.source_folder
        os.utime(os.path.join(here, "configure.in"), (0, 0))
        for rel in ("aclocal.m4", "Makefile.am", "config.h.in",
                    os.path.join("src", "Makefile.am")):
            os.utime(os.path.join(here, rel), (1, 1))
        for rel in ("config.guess", "config.sub", "configure", "install-sh",
                    "missing", "mkinstalldirs", "depcomp", "ltmain.sh"):
            os.utime(os.path.join(here, rel), (2, 2))
        for rel in ("Makefile.in", os.path.join("src", "Makefile.in")):
            os.utime(os.path.join(here, rel), (3, 3))

    def build(self):
        self._fix_timestamps()
        # [shell_getcwd] HMDFS denies getcwd() on the conan build tree and the
        # shared OHOS profile exports CONFIG_SHELL=/data/service/hnp/bin/bash.
        # autoconf's very first output is `checking build system type`
        # (configure line 1501), so anything that kills it earlier shows up as
        # *zero stdout, empty stderr, exit 1* -- exactly CI #70913 and #71162.
        # Two separate re-execs have to be suppressed:
        #   1. line 268-271  exec $SHELL "$0" --no-reexec  (SHELL=$CONFIG_SHELL)
        #   2. line 126-156  `case $CONFIG_SHELL in '')` -> hunt /bin:/usr/bin:$PATH
        #      for sh|bash|ksh|sh5 that supports $LINENO, then exec into it;
        #      on the worker the only match is /data/service/hnp/bin/bash.
        # Merely unsetting CONFIG_SHELL fixes (1) but re-opens (2), which is
        # why CI #71162 still failed.  *Setting* CONFIG_SHELL=/bin/sh pins both
        # and makes configure fall back to its sed-generated configure.lineno
        # path (jellyfish1/1.1.11 precedent: leave the shell to /bin/sh).
        # Absolute path avoids the toybox relative-path `pwd` defect (E386),
        # and PWD is exported so the shell's `pwd` takes the logical path
        # instead of getcwd() (adms/2.3.7, air-quality-sensor/0.1.5).
        # Zero patches added.
        os.environ["PWD"] = self.build_folder
        src = self.source_folder.replace("\\", "/")
        configure_args = " ".join(
            shlex.quote(a) for a in self._autotools_toolchain().configure_args
        )
        prefix = "env CONFIG_SHELL=/bin/sh SHELL=/bin/sh"
        # env="conanbuild" applies what AutotoolsToolchain generated (CC, CXX,
        # CFLAGS, LDFLAGS, AR/RANLIB/STRIP from the OHOS profile) - R33 forbids
        # leaning on an ambient compiler, and config.log of CI #80123 shows
        # CC='' precisely because the previous version ran configure with the
        # plain recipe environment.  The explicit `env CONFIG_SHELL=...` prefix
        # still wins over the profile's CONFIG_SHELL=/data/service/hnp/bin/bash
        # (see the shell_getcwd note above), so the shell fix is preserved.
        rc = self.run(
            f'{prefix} sh "{src}/configure" {configure_args}',
            ignore_errors=True, env="conanbuild",
        )
        if rc != 0:
            self._dump_configure_diagnostics(src, configure_args, prefix)
            raise ConanException(f"configure failed (exit {rc})")
        self.run(f"{prefix} make -j1", env="conanbuild")

    def _dump_configure_diagnostics(self, src, configure_args, prefix):
        """Make a silent configure failure legible instead of guessing.

        configure prints nothing at all when it dies early, so the CI log only
        ever says "Error 1 while executing".  Re-run under `sh -x` and print the
        tail of the trace plus which of the utilities configure relies on are
        actually reachable on this worker.
        """
        self.output.warning("configure failed; dumping shell/tool diagnostics")
        self.run(
            "for t in sh bash sed grep awk expr basename dirname mktemp tr cut "
            "sort uniq cat mkdir rm mv cp ln chmod diff cmp find file bc od dd "
            "head tail wc xargs readlink hostname uname printf test make perl "
            "python3; do printf 'TOOL %s = %s\\n' \"$t\" "
            "\"$(command -v $t 2>/dev/null || echo MISSING)\"; done"
        )
        self.run(
            f'{prefix} sh -x "{src}/configure" {configure_args} 2>&1 | tail -80',
            ignore_errors=True, env="conanbuild",
        )
        for log in ("config.log", os.path.join("build-release", "config.log")):
            path = os.path.join(self.build_folder, log)
            if os.path.isfile(path):
                self.run(f'tail -60 "{path}"')

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
