#!/usr/bin/env python3
"""Conan recipe — wmcube 1.0.2

wmcube is an X11 dockapp that renders tumbling 3D objects whose rotation
speed tracks the current CPU load.  Upstream: Cezary M. Kruk
(https://www.dockapps.net/wmcube), GPL-3.0 (the source tarball ships the
full GPL v3 text as `COPYING`).

Build system: one hand-written GNU Makefile (`wmcube/Makefile`).  The five
per-OS copies are not all clones of it: `Makefile.LINUX` is byte-identical to
it (diff rc=0), whereas `Makefile.FREEBSD`, `Makefile.NETBSD`,
`Makefile.OPENBSD` and `Makefile.SOLARIS` differ by 12, 28, 29 and 14 lines
(counted on the changed-line output of `diff Makefile Makefile.<OS>`): they
swap `OS`, `INCDIR`, `OSLIBS`, `CFLAGS` and the two rule lines.  The recipe
builds the plain `Makefile`, i.e. the LINUX variant -- no configure script,
no automake, and no upstream test suite
(the only targets are `all`, `clean`, `install`, `uninstall`; there is no
`check` target).

Two properties of that Makefile drive the whole recipe (details in notes.md):

* `CC`, `CFLAGS`, `LIBDIR`, `INCDIR`, `LIBS` are *assigned* inside the
  Makefile, so the environment cannot reach them.  make command-line
  variables *replace* those assignments instead of appending to them, so the
  recipe only takes over `CC` (hard-coded `gcc`) and empties the two stale
  X11R6 paths (`LIBDIR=-L/usr/X11R6/lib`, `INCDIR=-I/usr/X11R6/share/include`)
  and deliberately leaves `CFLAGS` alone to keep upstream's `-Wall -O2`.
* `CPPFLAGS` and `LDFLAGS` are *used but never assigned*, which makes them
  free channels for the Conan `conanbuild` environment.  That is how the
  dependency include/lib directories reach both the compile rule
  (`$(CC) $(OS) $(CPPFLAGS) $(CFLAGS) $(INCDIR) -c $<`) and the link rule,
  and it also places every `-L` ahead of the hard-coded `-lXext` in
  `$(CC) $(LDFLAGS) -o wmcube $^ -lXext $(LIBDIR) $(LIBS)` — which would
  otherwise be searched in the default directories only.

`make install` is never called: the upstream install rule runs
`chown root:root`, writes under `/usr`, and copies the man page into
`$(MANDIR)` without creating that directory first.  package() reproduces the
install layout with explicit copies.

One portability patch ships: `wmgeneral/wmgeneral.h:39` held a tentative
definition of the global X11 `display` connection, so every translation unit
that includes that header emitted its own copy.  Exactly two do --
`wmgeneral/wmgeneral.c:52` and `wmcube/wmcube.c:72`, i.e. `wmcube.o` plus
`../wmgeneral/wmgeneral.o` from the `OBJS` list (`wmcube/Makefile:22-25`);
`wmgeneral/misc.c:22-25` includes only `list.h`/`misc.h` and
`wmgeneral/list.c:34-38` only `list.h`/`stdlib.h` (`misc.h:4` is just
`<unistd.h>`, `list.h` includes nothing), so neither adds a copy.  Two copies
are enough: a 1998-era compiler merged them as common symbols, clang 15 (which
defaults to `-fno-common`) refuses to link with `ld.lld: error: duplicate
symbol: display`.  The patch turns the header entry into an `extern`
declaration and keeps the single definition in `wmgeneral.c` -- rec_priority 1
of knowledge/graph/E491.kv, whose forbid_1 rule rules out passing `-fcommon`
instead.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class WmcubeConan(ConanFile):
    name = "wmcube"
    version = "1.0.2"
    description = ("X11 dockapp showing the current CPU load as a spinning 3D "
                   "object (wmCube / wmcube by Cezary M. Kruk)")
    license = "GPL-3.0-or-later"
    homepage = "https://www.dockapps.net/wmcube"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Upstream LIBS = -lXpm -lXext -lX11 -lm, and every one of those three
        # X libraries is genuinely referenced by the sources:
        #   XpmCreatePixmapFromData -> libXpm   (wmcube/wmcube.c)
        #   XShapeCombineMask       -> libXext  (wmgeneral/wmgeneral.c)
        #   XOpenDisplay & friends  -> libX11
        # `shape.h` itself ships with xorgproto, so it is required directly.
        # The whole X11 graph here is on the cmd-pkgs 6.4.0 track; libxpm
        # refuses to pair with libx11/1.8.13, so 6.4.0 is used throughout.
        self.requires("libx11/6.4.0", transitive_headers=True, transitive_libs=True)
        self.requires("libxext/6.4.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("libxpm/3.5.17", transitive_headers=True, transitive_libs=True)
        self.requires("xorgproto/2025.1", transitive_headers=True)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"wmcube supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        # `conan_data` is the spelling used across this repository's recipes
        # (Conan 2.29 baseline).
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------
    def generate(self):
        # The Makefile reads CPPFLAGS/LDFLAGS from the environment (it never
        # assigns them), so AutotoolsToolchain + AutotoolsDeps are enough to
        # inject every dependency header/library directory — no command-line
        # flag surgery required.
        AutotoolsToolchain(self).generate()
        AutotoolsDeps(self).generate()

    def _make_dir(self):
        return os.path.join(self.source_folder, "wmcube")

    def build(self):
        # Applies the one portability patch declared in conandata.yml (the
        # header-level tentative definition of `display`; see the module
        # docstring).  The hook stays wired unconditionally: G1 expects it in
        # the recipe, and it is the only entry point for a future 1.0.2.x.
        apply_conandata_patches(self)

        # R33: the compiler comes from the Conan conf/profile, never from a
        # shell variable.  The profile spells the C entry as "c".
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("c") or "clang"

        # Command-line variables replace the Makefile assignments (they do
        # not append), hence:
        #   CC=...    to beat `CC = gcc`
        #   LIBDIR=   / INCDIR= emptied to drop the hard-coded
        #             -L/usr/X11R6/lib and -I/usr/X11R6/share/include
        #             (the real directories arrive through CPPFLAGS/LDFLAGS)
        #   CFLAGS    deliberately NOT overridden, so `-Wall -O2` survives.
        # R9: -j1 — the implicit `.c.o` rule writes ../wmgeneral/*.o, so a
        # parallel build races on the shared object directory.
        self.run(f'make -j1 CC="{cc}" LIBDIR= INCDIR=',
                 env="conanbuild", cwd=self._make_dir())

    def package(self):
        make_dir = self._make_dir()
        src_root = self.source_folder

        bin_dir = os.path.join(self.package_folder, "bin")
        copy(self, "wmcube", src=make_dir, dst=bin_dir)

        # OBJDIR = $(PREFIX)/share/wmcube — the 3D object definitions.
        obj_dir = os.path.join(self.package_folder, "share", "wmcube")
        copy(self, "*.wmc", src=os.path.join(src_root, "3D-objects"), dst=obj_dir)

        # DOCDIR = $(PREFIX)/doc/wmcube-$(VERSION)
        doc_dir = os.path.join(self.package_folder, "share", "doc",
                               f"wmcube-{self.version}")
        for name in ("README", "CHANGES", "INSTALL", "THANKS"):
            copy(self, name, src=src_root, dst=doc_dir)

        # MANDIR = $(PREFIX)/man/man1
        copy(self, "wmcube.1", src=make_dir,
             dst=os.path.join(self.package_folder, "share", "man", "man1"))

        copy(self, "COPYING", src=src_root,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Command-line/GUI application: no headers, no libraries to link.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
        self.conf_info.define("user.wmcube:bin", "wmcube")
