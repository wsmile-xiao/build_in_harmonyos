#!/usr/bin/env python3
"""Conan recipe for pMARS 0.9.5 — portable Core War simulator (ICWS'94).

Build system: bare Makefile. Upstream ships four of them under ``src/``
(``Makefile``, ``Makefile.clang``, ``Makefile.djg``, ``Makefile.wat``) and has
no configure script, so this recipe drives make directly.

Why ``Makefile.clang`` is the one we drive:
  * its ``CFLAGS`` is a *plain* assignment, so the recipe can set the exact
    flag set; the generic ``Makefile`` uses ``CFLAGS += -DXWINGRAPHX``, which a
    command-line assignment can only extend, never remove;
  * it contains no X11 wiring at all (the generic one hardcodes
    ``LIB = -L/usr/X11R6/lib -lX11``);
  * ``sim.o`` pulls the display modules in via ``#include`` (``sim.c`` includes
    ``curdisp.c``), which both makefiles express the same way.

Display variant (compile-time switch, see notes.md):
  * upstream default ``-DXWINGRAPHX``  -> X11 graphics;
  * this recipe ``-DCURSESGRAPHX``     -> terminal (curses) graphics.
  ``src/config.h`` keeps every display switch *commented out*, i.e. the display
  layer is selected purely through CFLAGS. HarmonyOS PC exposes no X display
  server to native CLI packages, while it does provide a terminal (pty verified
  on-device), so the X11 layer is switched off simply by not defining
  ``XWINGRAPHX`` — no source edit and no platform macro involved.

Portability notes (full write-up in notes.md):
  * ``curdisp.c`` reaches into the opaque ``WINDOW`` struct (``_curx``/``_cury``)
    in five places; the ``ncurses/6.6`` artifact published by this repository is
    an opaque release (``include/curses.h:152`` is ``#define NCURSES_OPAQUE 1``),
    which keeps that struct incomplete, so the direct field reads are a hard
    compile error. Patch ``0001-curdisp-opaque-window-accessors.patch`` switches
    those to the public ``getcurx()``/``getcury()`` accessors, which
    ``libncursesw.a`` exports as real functions. ``curdisp.c`` already uses the
    portable ``getyx()`` macro nearby, so this is upstream's own style.
    Scope note: this one is a generic ncurses>=6 opaque-struct incompatibility --
    it also fails on any Linux ncurses>=6 published with ``NCURSES_OPAQUE=1``.
    Pure compile-time type visibility, no syscall/ioctl/device access involved,
    so it is **not** an OHOS platform capability gap. The OHOS-specific items are
    the X11 section above and the ``run=True`` terminfo bullet below.
  * The published ``ncurses/6.6`` package ships wide-character **static**
    libraries only (``libncursesw.a``; no ``libncurses.a``, no ``.so``), hence
    ``-lncursesw`` and no ``NEEDED`` entry for ncurses in the final binary.
  * ncurses resolves the terminal database through its ``runenv_info``
    (``TERMINFO``/``TERMINFO_DIRS``), so the requirement is declared
    ``run=True``: without it the packaged binary exits with
    "ncurses: cannot initialize terminal type" on the first display call.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class PmarsConan(ConanFile):
    name = "pmars"
    version = "0.9.5"
    package_type = "application"
    description = (
        "pMARS — portable Memory Array Redcode Simulator: a Core War simulator "
        "implementing the ICWS'94 standard with a terminal (curses) core display"
    )
    license = "GPL-2.0-or-later"
    homepage = "http://www.koth.org/pmars/"
    url = "http://www.koth.org/pmars/pmars-0.9.5.zip"
    topics = ("corewar", "redcode", "icws94", "simulator", "curses", "game")

    settings = "os", "arch", "compiler", "build_type"

    # Upstream release 0.9.5 (ChangeLog entry "Release 0.9.5", man page
    # ".TH PMARS 6 ... PMARS v0.9.5", src/global.h "#define PMARSVER 95").
    def validate(self):
        # R32: os check must accept OHOS alongside Linux, never `== "Linux"`.
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "pmars supports Linux and OHOS only, got '{0}'".format(self.settings.os)
            )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # run=True is load-bearing, not decoration: the published ncurses/6.6
        # recipe exports TERMINFO/TERMINFO_DIRS through runenv_info, and the
        # packaged pmars aborts on the first curses call without that env.
        self.requires("ncurses/6.6", run=True)

    def layout(self):
        basic_layout(self)
        # In-tree build: upstream makefiles compile into src/ and offer no
        # out-of-tree variant, so keep build_folder at the recipe root.
        self.folders.build = "."

    def source(self):
        # Official zip, sha256 pinned in conandata.yml. It has *no* common
        # top-level directory (entries are src/, doc/, config/, warriors/, ...),
        # so strip_root must not be used here.
        get(self, **self.conan_data["sources"], destination=self.source_folder)

    def _ncurses_folder(self):
        return self.dependencies["ncurses"].package_folder

    def build(self):
        apply_conandata_patches(self)
        # R33: the compiler comes from the Conan profile conf, never from a
        # bare ${CC}/${CFLAGS} shell variable (those are empty on the release
        # worker).
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang") if compilers else "clang"

        ncurses = self._ncurses_folder()
        src_dir = os.path.join(self.source_folder, "src")
        # -DCURSESGRAPHX selects the terminal display; XWINGRAPHX is deliberately
        # absent, which is how the X11 layer is turned off at compile time.
        self.run(
            'make -C "{src}" -f Makefile.clang -j1 CC="{cc}" '
            'CPPFLAGS="-I{nc}/include" '
            'CFLAGS="-O -DEXT94 -DCURSESGRAPHX -DPERMUTATE -DRWLIMIT" '
            'LDFLAGS="-L{nc}/lib" LDLIBS="-lncursesw"'.format(
                src=src_dir, cc=cc, nc=ncurses
            )
        )
        # Upstream ships no check/test target (no Makefile in the tree defines
        # `check` or `test`; see notes.md for the grep evidence). The upstream
        # authored checks are the `;assert` directives inside warriors/*.red,
        # which are evaluated at assembly time; they are exercised by
        # test_package/ because running them here would require a terminal.

    def package(self):
        pkg = self.package_folder
        src_dir = os.path.join(self.source_folder, "src")

        copy(self, "pmars", src=src_dir, dst=os.path.join(pkg, "bin"))
        # Data the simulator needs to be useful out of the box: the sample
        # warriors (which carry the upstream `;assert` conformance directives)
        # and the KotH option files.
        copy(self, "*.red",
             src=os.path.join(self.source_folder, "warriors"),
             dst=os.path.join(pkg, "res", "warriors"))
        copy(self, "*.opt",
             src=os.path.join(self.source_folder, "config"),
             dst=os.path.join(pkg, "res", "config"))
        copy(self, "pmars.txt",
             src=os.path.join(self.source_folder, "doc"),
             dst=os.path.join(pkg, "res", "doc"))
        copy(self, "COPYING",
             src=self.source_folder,
             dst=os.path.join(pkg, "res", "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["res"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
