#!/usr/bin/env python3
"""Conan recipe for pal 0.4.3 -- a text-mode calendar (upstream bare Makefile).

Every build-side decision below was measured on HarmonyOS PC; the evidence logs
are listed in ``notes.md``.  The four non-obvious ones:

* ``src/Makefile.defs`` assigns every variable with a plain ``=``, so *make
  ignores CFLAGS/LDFLAGS coming from the environment* and a command-line
  assignment replaces the whole expression.  Conan's flags therefore go in
  through ``OPT`` (the sole input to ``CFLAGS``), while the dependency flags
  stay with the patched pkg-config lines.  Setting ``self.buildenv("CFLAGS")``
  alone would look green but drop every Conan include/library path.
* Upstream hard-codes ``-lncurses``.  The Conan ``ncurses`` package only ships
  the wide-character library (``libncursesw.a``, no ``libncurses.a``) and
  ``gettext``/``textdomain`` need ``-lintl`` from the glib package.  Patch
  0001 resolves both by letting pkg-config answer (patch 0001 + patch 0002 are
  the two files in ``patches/``).
* On OpenHarmony an ELF that has been ``strip``ped cannot be executed --
  ``execve`` fails with "Operation not permitted" (rc 126).  Upstream strips
  unconditionally right after linking, so patch 0001 makes it ``$(STRIP)`` and
  we pass ``STRIP=true`` (same prescription as the abduco/0.6 precedent).
* ``make install`` is unusable on this platform: it runs ``install -m 0755 -o
  root`` (there is no ``install`` program and we are not root), prompts through
  an interactive ``rm -ri`` and needs ``msgfmt``/``gzip``.  ``package()`` copies
  the deliverables itself.
"""
import os

from conan import ConanFile
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class PalConan(ConanFile):
    name = "pal"
    version = "0.4.3"
    description = (
        "pal is a text-mode calendar and appointment manager. It tracks "
        "holidays, birthdays and anniversaries and prints a monthly "
        "calendar with the events for the requested dates."
    )
    license = "GPL-2.0-or-later"
    homepage = "https://palcal.sourceforge.net"
    url = ""  # CI fills this
    topics = ("calendar", "curses", "cli", "readline")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    # ``-DPREFIX="$(prefix)"`` is compiled into the binary and pal falls back
    # to ``<PREFIX>/share/pal/*.pal`` (see input.c).  Keep the two in sync with
    # where package() actually installs the data, i.e. the package folder.
    _OPT_BY_BUILD_TYPE = {
        "Debug": "-g -Wall",
        "Release": "-O2 -Wall",
        "RelWithDebInfo": "-O2 -g -Wall",
        "MinSizeRel": "-Os -Wall",
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Direct build-time consumers of headers/symbols (R36): glib for
        # gslist/gdate/gettext, readline for the line editor, ncurses for the
        # coloured calendar (only the *wide* library is published).
        self.requires("glib/2.84.0.1")
        self.requires("readline/8.3")
        self.requires("ncurses/6.6")

    def build_requirements(self):
        # Patch 0001 keeps upstream's "resolve flags with pkg-config" scheme,
        # so pkg-config has to be on PATH during build().
        self.tool_requires("pkgconf/3.0.5")

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def generate(self):
        VirtualBuildEnv(self).generate()
        PkgConfigDeps(self).generate()
        # PkgConfigDeps writes the .pc files but does not put the generators
        # folder on PKG_CONFIG_PATH for a raw-make consumer.
        env = Environment()
        env.define_path("PKG_CONFIG_PATH", self.generators_folder)
        env.vars(self, scope="build").save_script("conanbuild_pkgconfig")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # ``tools.build:compiler_executables`` is a *dict* conf; Conan 2.29 has
        # no "…:c" sub-key form (the Makefile template's variant raises
        # "[conf] 'tools.build:compiler_executables:c' does not exist in
        # configuration list"), so read the dict and index it -- same as the
        # abduco/0.6 precedent.  R33: never take the compiler from ${CC}.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang") if compilers else "clang"
        opt = self._OPT_BY_BUILD_TYPE.get(str(self.settings.build_type), "-O2 -Wall")
        # The upstream ``info:`` target echoes the resolved CFLAGS/CPPFLAGS/
        # LDFLAGS before anything compiles, so the flag injection is auditable
        # in the build log.
        self.run(
            'make -C src -j1 CC={} STRIP=true OPT="{}" prefix="{}"'.format(
                cc, opt, self.package_folder
            )
        )

    def package(self):
        src = self.source_folder
        pkg = self.package_folder

        copy(self, "pal", os.path.join(src, "src"), os.path.join(pkg, "bin"),
             keep_path=False)
        # The build ran as an ordinary user; make sure the deliverable is +x.
        binary = os.path.join(pkg, "bin", "pal")
        os.chmod(binary, 0o755)

        # Global calendar data + the system-wide configuration template.
        #
        # pal bootstraps ~/.pal/pal.conf by opening "/etc/pal.conf" and, when
        # that fails, ``PREFIX "/share/pal/pal.conf"`` (src/input.c:570-582);
        # if neither exists it prints "ERROR: This indicates an improper
        # installation." and starts with an empty config, so none of the
        # shipped .pal calendars get loaded.  Upstream's install-share puts the
        # template under ${DESTDIR}/etc -- a path that is independent of
        # $(prefix) and not writable for a packaged/conan install -- so the
        # runtime-discovered copy under share/pal/ is the one that matters.
        copy(self, "*.pal", os.path.join(src, "share"),
             os.path.join(pkg, "share", "pal"))
        copy(self, "pal.conf", src, os.path.join(pkg, "share", "pal"),
             keep_path=False)
        copy(self, "pal.conf", src, os.path.join(pkg, "etc"), keep_path=False)

        # install-man does ``sed 's/PAL_VERSION/.../' pal.1.template | gzip``.
        # pal.1.template contains no PAL_VERSION placeholder at all (grep -c
        # returns 0) and the device has no gzip, so ship the plain man page.
        copy(self, "pal.1.template", src, os.path.join(pkg, "share", "man", "man1"),
             keep_path=False)
        os.rename(os.path.join(pkg, "share", "man", "man1", "pal.1.template"),
                  os.path.join(pkg, "share", "man", "man1", "pal.1"))

        copy(self, "COPYING", src, os.path.join(pkg, "licenses"), keep_path=False)
        os.rename(os.path.join(pkg, "licenses", "COPYING"),
                  os.path.join(pkg, "licenses", "LICENSE"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        # This is an end-user command, not a library: nothing to link against.
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = []
        # ``pal`` links libglib-2.0.so.0 dynamically, so a consumer needs the
        # glib/readline run-time libraries on LD_LIBRARY_PATH.  The declared
        # requires() carry that: Conan's VirtualRunEnv walks them.
