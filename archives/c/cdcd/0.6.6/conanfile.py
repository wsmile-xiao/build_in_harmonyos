#!/usr/bin/env python3
"""Conan recipe for cdcd 0.6.6 — command line CD player on libcdaudio (Autotools).

Upstream: SourceForge project libcdaudio's cdcd release
(https://sourceforge.net/projects/libcdaudio/files/cdcd/0.6.6/ , homepage
http://libcdaudio.sourceforge.net/ — the same URL Debian's copyright file
declares).  The tarball ships a pre-generated autoconf-2.59/automake-1.8
configure + Makefile.in, so no autoreconf is needed (CI worker PATH has no
autotools — device-facts §4.2; AM_MAINTAINER_MODE defaults to disabled so
nothing rebuilds the generated files either).

Deliverable: `package_type = "application"` — only bin/cdcd (plus the man
page and info doc installed by `make install`), no public libs/headers.

Five portability patches (all dry-run verified in conandata order against a
clean tarball tree — `$TASK_DIR/patchwork/final-verify`, 5/5 applied):

  0001 config.sub: recognize aarch64.  The 1996-era config.sub rejects the
        triplet outright (probe: `sh config.sub aarch64-unknown-linux-gnu`
        → "Invalid configuration … not recognized") — configure would die
        the moment --build/--host is validated.
  0002 configure: `umask 077` → `umask 000` (both occurrences) for the
        config.status confstat temp dir.  HMDFS makes 0700 dirs
        untraversable (E011/E206 family): probe showed
        `(umask 077 && mktemp -d …)` → drwx--S--- → writes EACCES, while
        `umask 000` → drwxrws--x → writable.
  0003/0004 configure + configure.ac: `AC_CHECK_LIB(curses, tputs)` →
        `-lncursesw`.  conan's ncurses package ships only wide-char library
        names (libncursesw/libformw/… — no libcurses at all), so the tputs
        probe hard-fails configure ("cannot find the curses library") until
        the probe name matches the package.  configure.ac carries the same
        edit so a future autoreconf cannot regress it.
  0005 cmd_cdcd.c: `CPPFunction` → guarded `rl_completion_func_t`.
        readline ≥ 6 removed the CPPFunction typedef; we link readline/8.3
        (probe: `error: use of undeclared identifier 'CPPFunction'`), and
        the guard keeps the original branch for ancient readline.

Device-probed configure facts (2026-09-23, `$TASK_DIR/explore-*`):

  * The 1996 config.guess cannot guess this device (rc=1, empty output), so
    `--build`/`--host` must be passed explicitly.  conan does NOT inject
    them here because build profile == host profile (cross_building False).
    Triplet is `aarch64-unknown-linux-gnu` for both: config.sub accepts it
    after 0001, and `linux-gnu` (not linux-ohos) keeps configure's
    `case "$host_os" in *linux*` branch, which is what defines
    HAVE_CDAUDIO / DEFAULT_DEVICE (cdck 0.7.0 precedent).
  * `--with-libcdaudio-prefix=<libcdaudio package folder>` is load-bearing:
    (1) conanbuild PATH does not carry *host* requires' bindirs, so
    AC_PATH_PROG would never find `libcdaudio-config`; the macro's prefix
    path sets LIBCDAUDIO_CONFIG to an absolute path instead.  (2) The
    packaged config script bakes `prefix=/`, which would emit the bogus
    `-I//include -L//lib`; the macro re-derives -I/-L from the prefix we
    pass.  Probe: configure rc=0 and "libcdaudio - version >= 0.99.0…
    yes" (the AC_TRY_RUN conftest really executed — build == host).
  * SHELL/CONFIG_SHELL come from the ohos-aarch64 profile
    (/data/service/hnp/bin/bash — exists, bash 5.3 probed) and configure
    itself runs cleanly under toybox `/bin/sh` (separate probe: configure
    AND make both rc=0 invoked via `/bin/sh`), so no shell override is
    needed (unlike cdck, whose image lacked hnp bash at the time).

Upstream ships **no test suite**: no tests/ directory, no TESTS /
check_PROGRAMS / check target in either Makefile.am (root + doc/), and the
upstream git HEAD (3fac243, 2026-09) also has zero test registrations
(grep rc=1) — N=0 both faces.  `make check` is the automake default empty
target and is **really executed** in build() so the emitted
HMBS_UPSTREAM_TEST_RESULT no_tests marker is machine evidence from a run
command, not an assertion (cdck precedent).

test_package pre-seeds `$HOME/.cdcdrc` — mandatory: `cdcdrc_read()` runs
BEFORE getopt in main(), and a missing rc file drops into the interactive
first-run wizard (cdcdrc_manual_configuration → get_input_text on stdin)
which would hang a headless test forever.
"""

import json
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class CdcdConan(ConanFile):
    name = "cdcd"
    version = "0.6.6"
    description = ("cdcd - command line / console CD player with CDDB and "
                   "CD Index lookup, built on libcdaudio")
    license = "GPL-2.0-or-later"
    homepage = "http://libcdaudio.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("cd-player", "cdda", "cddb", "libcdaudio", "cli")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # All three are probed directly by configure:
        #   AM_PATH_LIBCDAUDIO (cdaudio.h + -lcdaudio),
        #   AC_CHECK_LIB(readline, rl_completion_matches),
        #   AC_CHECK_LIB(ncursesw, tputs)   [after 0003/0004]
        # (readline also pulls ncurses transitively; declared explicitly
        #  because our patched probe links it directly.)
        self.requires("libcdaudio/0.99.12p2")
        self.requires("readline/8.3")
        self.requires("ncurses/6.6")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"cdcd/0.6.6 is adapted for Linux and OHOS, not {self.settings.os}")
        # Non-armv8 arches are not claimed: the bundled 1996 config.sub only
        # knows aarch64 after patch 0001, and config.guess cannot guess this
        # device at all (rc=1).  Without the explicit triplet below such a
        # build fails loudly at "cannot guess build type" — honest, not silent.

    def layout(self):
        basic_layout(self)

    def source(self):
        # filename= is load-bearing: conan deduces it from url[0], and the
        # canonical SourceForge URL ends in "/download" (no extension) →
        # unzip would fall into the zip branch and raise BadZipFile on a
        # perfectly good gzip (sha256 already verified at that point).
        # Pinning the real .tar.gz name selects the tar branch (trial-create
        # rc=1 evidence: `$TASK_DIR/trial-create.log`).
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="cdcd-0.6.6.tar.gz")

    def generate(self):
        tc = AutotoolsToolchain(self)
        if str(self.settings.arch) == "armv8":
            # 1996 config.guess rc=1 on this device → explicit triplets are
            # mandatory (conan injects none: build profile == host profile).
            # linux-gnu keeps configure's *linux* branch (HAVE_CDAUDIO).
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-gnu",
            ])
        # Load-bearing (see module docstring): absolute LIBCDAUDIO_CONFIG
        # discovery + correct -I/-L re-derivation from the conan package dir.
        libcdaudio = self.dependencies["libcdaudio"]
        tc.configure_args.append(
            f"--with-libcdaudio-prefix={libcdaudio.package_folder}")
        tc.generate()
        # Injects CPPFLAGS (all deps' -I), LDFLAGS (-L) and LIBS (-l
        # formw/menuw/panelw/ncursesw/readline/history/cdaudio) into the
        # conanbuild env that Autotools.configure/make/install run under.
        AutotoolsDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"cdcd/0.6.6 supports Linux and OHOS targets only, not {self.settings.os}")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()
        # Upstream registers zero Automake TESTS; `make check` is the empty
        # default target.  Run it for real so the no_tests marker below is
        # machine evidence from an executed command (cdck precedent).
        autotools.make(target="check")
        self._emit_no_tests_marker()

    def _emit_no_tests_marker(self):
        upstream = {
            "status": "no_tests",
            "framework": "autotools",
            "command": "make check",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "cdcd-0.6.6 audited: no tests/ or test/ directory in the "
                      "54-file tarball; Makefile.am (root) and doc/Makefile.am "
                      "define only SUBDIRS/bin_PROGRAMS/man_MANS/info_TEXINFOS "
                      "with no TESTS, check_PROGRAMS or check target; upstream "
                      "git HEAD 3fac243 (2026-09) also has zero test "
                      "registrations (grep rc=1); make check is the automake "
                      "default empty target executing zero cases",
        }
        msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
        print(msg, flush=True)
        self.output.info(msg)

    def package(self):
        # `make install` with the toolchain's --prefix=/ and conan's injected
        # DESTDIR=package_folder: probe (explore-build/install.log, rc=0)
        # staged exactly bin/cdcd + man/man1/cdcd.1 + info/cdcd.info, with
        # the missing install-info guarded by configure's `else :` branch.
        Autotools(self).install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
