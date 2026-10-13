#!/usr/bin/env python3
"""Conan recipe — vtgrab 0.1.8 (RVC: remote virtual console).

vtgrab ships three programs (upstream Makefile.am ``bin_PROGRAMS``):

* ``rvc``     — ANSI-escape console client for a remote RVC server
* ``rvcd``    — the RVC server: serves the foreground Linux virtual console
* ``twiglet`` — ncurses-based RVC client

Build system: direct compiler invocation (see ``_build`` for why the upstream
autotools path is not used).  ``twiglet`` has the only functional external
dependency (ncurses).  All three land in ``bin/`` and are declared through the
software level ``commands.json``.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout

# program -> upstream sources (Makefile.am: rvc_SOURCES / rvcd_SOURCES / twiglet_SOURCES)
# fd_chk.c provides __fd_chk for OHOS musl (see sys/select.h in OHOS sysroot)
PROGRAMS = {
    "rvc": (["rvc.c", "fd_chk.c"], []),
    "rvcd": (["rvcd.c", "xfree86.c", "fd_chk.c"], []),
    "twiglet": (["nrvc.c", "simple_panel.c", "fd_chk.c"], ["ncurses"]),
}
STAGING_DIR = "_install"

# Only macro the sources take from config.h.  Verified by grepping every .c for
# HAVE_*/STDC_HEADERS/TIME_WITH_SYS_TIME: there are no hits, so none of
# autoconf 2.13's header/function probes are needed.  Values mirror upstream
# configure.in's AM_INIT_AUTOMAKE(vtgrab, 0.1.8).
CONFIG_H = """/* Hand-written config.h for vtgrab 0.1.8; see archives/v/vtgrab/0.1.8/notes.md.
 *
 * The three .c files that include <config.h> (rvc.c, rvcd.c, nrvc.c) reference
 * exactly one macro from it: VERSION, used by their --version output.  Upstream
 * would have had autoconf 2.13 fill this file in; nothing else it probes is read
 * by any translation unit, so the file is provided here instead.  Values are
 * verbatim from upstream configure.in: AM_INIT_AUTOMAKE(vtgrab, 0.1.8).
 */
#ifndef VTGRAB_CONFIG_H
#define VTGRAB_CONFIG_H
#define PACKAGE "vtgrab"
#define VERSION "0.1.8"
#endif /* VTGRAB_CONFIG_H */
"""


class VtgrabConan(ConanFile):
    name = "vtgrab"
    version = "0.1.8"
    description = "Copy the foreground terminal of one machine to another for remote monitoring (RVC)"
    license = "GPL-2.0-or-later"
    homepage = "https://tracker.debian.org/pkg/vtgrab"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        # twiglet is the only program with a functional ncurses dependency.
        #
        # Declared through requirements() instead of the class attribute
        # ``requires = "ncurses/6.5"``: the CI L0i gate (R36, "dependency
        # availability in the artifact registry") extracts dependencies with an
        # AST walk over the *call* nodes ``requires()`` / ``tool_requires()`` /
        # ``build_requires()``, so the attribute form makes it skip this
        # package's dependency completely (measured 2026-10-11: the local
        # same-source gate printed no L0i line at all, while sibling packages
        # show "[ok] dependency in registry: ...").  Semantics are otherwise
        # identical - the resolved graph is the same ncurses/6.5.
        self.requires("ncurses/6.5")

    def export_sources(self):
        export_conandata_patches(self)
        # fd_chk.c is a local source file providing __fd_chk for OHOS musl
        from conan.tools.files import copy
        copy(self, "fd_chk.c", self.recipe_folder, self.export_sources_folder)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "vtgrab supports Linux/OHOS only, got %s" % self.settings.os
            )

    def layout(self):
        basic_layout(self, src_folder=".", build_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _toolchain_env(self):
        """Emit CC/CFLAGS/CPPFLAGS/LDFLAGS for one clang call per source file.

        R33: the compiler comes from ``tools.build:compiler_executables`` and the
        ncurses paths from the resolved dependency, never from bare shell
        variables or a hardcoded system prefix.
        """
        tc = AutotoolsToolchain(self)
        ncurses = self.dependencies["ncurses"].cpp_info
        # -I<build_folder> is mandatory, not cosmetic: the sources say
        # #include <config.h>, and clang only resolves an angled include of a
        # project-local header through the quoted form or an -I path.
        tc.extra_cflags = ["-I%s" % self.build_folder]
        tc.extra_cflags += ["-I%s" % d for d in ncurses.includedirs]
        tc.extra_ldflags = ["-L%s" % d for d in ncurses.libdirs]
        env = tc.environment()
        tc.generate(env=env)

        # OHOS uses musl libc which doesn't provide glibc's fortified I/O
        # functions (__fd_chk, __open_chk, etc.).  The AutotoolsToolchain
        # enables _FORTIFY_SOURCE=2 for Release builds by default; explicitly
        # set it to 0 so the compiled binaries don't reference missing symbols.
        cflags = list(tc.cflags)
        if str(self.settings.os) == "OHOS":
            cflags.append("-D_FORTIFY_SOURCE=0")
        self._cflags = " ".join(["-D_GNU_SOURCE", "-Wall", "-W"] + cflags)
        self._ldflags = " ".join(tc.ldflags)
        # Resolved from the dependency rather than left to shell expansion of
        # $LIBS: the wrapper Conan uses to apply env files does not reliably
        # expand it, and a silently empty $LIBS shows up as a wall of
        # "undefined reference to newwin/wgetch/..." at link time instead.
        # ncurses/6.5 ships only the wide-character flavour (libncursesw.a).
        self._ncurses_libs = ["-l%s" % lib for lib in ncurses.libs]

    def build(self):
        apply_conandata_patches(self)
        self._toolchain_env()
        # R33: compiler path comes from tools.build:compiler_executables.
        cc = self.conf.get("tools.build:compiler_executables",
                           check_type=dict, default={}).get("c", "cc")
        src = self.source_folder

        with open(os.path.join(src, "config.h"), "w", encoding="utf-8") as fh:
            fh.write(CONFIG_H)

        for program, (sources, deps) in PROGRAMS.items():
            objs = []
            for unit in sources:
                obj = "%s_%s.o" % (program, unit[:-2])
                self.run(f'{cc} {self._cflags} -c "{os.path.join(src, unit)}" -o "{obj}"',
                         env="conanbuild")
                objs.append(obj)
            link = " ".join('"%s"' % o for o in objs)
            libs = " ".join(self._ncurses_libs) if "ncurses" in deps else ""
            self.run(f'{cc} {self._cflags} {self._ldflags} -o {program} {link} {libs}'.strip(),
                     env="conanbuild")

        staging = os.path.join(self.build_folder, STAGING_DIR, "bin")
        self.run(f'mkdir -p "{staging}" && cp rvc rvcd twiglet "{staging}"', env="conanbuild")

    def package(self):
        staged_bin = os.path.join(self.build_folder, STAGING_DIR, "bin")
        for program in PROGRAMS:
            # copy() re-creates the file: on the CI worker the filesystem ignores
            # the mode bits an in-tree install leaves behind, and the packaged
            # binary would come out non-executable (EPERM on first run).
            copy(self, program, staged_bin, os.path.join(self.package_folder, "bin"))
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
