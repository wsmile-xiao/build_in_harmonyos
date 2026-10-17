#!/usr/bin/env python3
"""Conan recipe — lcs 4.07.4b (Liberal Crime Squad, SourceForge SVN r738).

Autotools (autoreconf bootstrap) ncurses roguelike, packaged as an
application.  There is no official tarball for this SVN revision —
conandata.yml pins each of the 188 build-relevant upstream files
individually via the official !svn/bc/738 DAV URLs, so source()
downloads them one by one instead of get()-ing an archive.

Upstream tree notes:
  * configure.ac hardcodes the ncurses wide-character header as
    <ncursesw/ncurses.h> and the library probe as -lncursesw/-lncurses
    (AC_CHECK_LIB on addch/add_wch + AC_SEARCH_LIBS on initscr).  The
    Conan ncurses package installs FLAT headers (ncurses.h at the
    include root; the widechar API is in the same header and the same
    libncursesw.a), so the wide probe never fires, the plain probe
    finds no libncurses.a, and configure dies with "You need ncurses!".
    Patch 0001 teaches configure.ac that a flat ncurses.h with add_wch
    in libncursesw is a wide-character ncurses.
  * includes.h maps USE_NCURSES_W -> <ncursesw/ncurses.h>; patch 0001
    makes the USE_NCURSES_W case include the flat <ncurses.h> when the
    subdirectory header is absent.
  * The build needs no other changes: art/ runtime data is installed by
    dist_art_DATA to $(datadir)/lcs/art/ and the binary locates it at
    runtime through the compile-time INSTALL_DATA_DIR (src/Makefile.am
    injects -DINSTALL_DATA_DIR=\"$(datadir)\"), so a plain
    `make install prefix=<package_folder>` closes the loop.
  * dumpcaps.cpp is a dev tool with its own main(); upstream never
    builds it (not in bin_PROGRAMS) — left untouched.
"""

import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (apply_conandata_patches, download,
                               export_conandata_patches)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.gnu.get_gnu_triplet import _get_gnu_triplet
from conan.tools.layout import basic_layout

# Exact Autoconf temp-dir umask idioms (AS_INIT-generated "Create a
# (secure) tmp directory" block, present verbatim in both configure and
# the config.status it spawns):
#   old autoconf (<= 2.71, e.g. the CI host's hnp autoconf):
#     tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&
#     (umask 077 && mkdir "$tmp")
#   autoconf 2.72:
#     tmp=`(umask 000 && mktemp -d "./confXXXXXX") 2>/dev/null` &&
#     (umask 000 && mkdir "$tmp")
_UMASK_TMP_MKTEMP = {
    "077": 'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
    "000": 'tmp=`(umask 000 && mktemp -d "./confXXXXXX") 2>/dev/null`',
}
_UMASK_TMP_MKDIR = {
    "077": '(umask 077 && mkdir "$tmp")',
    "000": '(umask 000 && mkdir "$tmp")',
}


def _fix_tmpdir_umask(path):
    """E114: HMDFS forces setgid on directories, so the Autoconf
    temp-dir block above (`umask 077 && mktemp -d` / `umask 000 &&
    mktemp -d`) creates a drwx--S--- dir that is not writable even by
    its owner, and config.status dies with "could not setup config
    files machinery" when it redirects into $ac_tmp/subs1.awk.  Change
    both umask occurrences to 022 (the HMDFS-friendly mode verified
    locally: mktemp dirs stay owner-writable).  The same block
    propagates verbatim into config.status, so patching configure
    fixes both.  Fail-closed: a configure carries exactly one of the
    two idiom pairs (077 or 000, per the generating autoconf version)
    with exactly one occurrence of each member; anything else aborts
    the build, as does any old form surviving the rewrite."""
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    hits = {}
    for old_umask in ("077", "000"):
        for pattern in (_UMASK_TMP_MKTEMP[old_umask],
                        _UMASK_TMP_MKDIR[old_umask]):
            hits[pattern] = data.count(pattern)
    found_pairs = {
        umask for umask in ("077", "000")
        if hits[_UMASK_TMP_MKTEMP[umask]] or hits[_UMASK_TMP_MKDIR[umask]]
    }
    if len(found_pairs) != 1:
        raise ConanException(
            f"configure umask fix: cannot identify a single Autoconf "
            f"temp-dir umask idiom pair (077/000), pattern hits: {hits}"
        )
    old_umask = found_pairs.pop()
    for pattern in (_UMASK_TMP_MKTEMP[old_umask],
                    _UMASK_TMP_MKDIR[old_umask]):
        count = hits[pattern]
        if count != 1:
            raise ConanException(
                f"configure umask fix: expected exactly 1 occurrence "
                f"of {pattern!r}, found {count}"
            )
        data = data.replace(pattern, pattern.replace(old_umask, "022"))
    for old_umask in ("077", "000"):
        for pattern in (_UMASK_TMP_MKTEMP[old_umask],
                        _UMASK_TMP_MKDIR[old_umask]):
            if pattern in data:
                raise ConanException(
                    f"configure umask fix: old pattern {pattern!r} "
                    f"still present after rewrite"
                )
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)


class LcsConan(ConanFile):
    name = "lcs"
    version = "4.07.4b"
    description = "Liberal Crime Squad — a satirical console roguelike game"
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/lcsgame/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires("ncurses/6.5")

    def build_requirements(self):
        # build() bootstraps with `autoreconf -fvi` (upstream ships
        # configure.ac only), but the CI host does not guarantee a
        # system aclocal/automake (only the autoconf suite is present
        # under /data/service/hnp/bin).  Pull automake in as a
        # tool_require so aclocal/automake come from Conan instead of
        # the host (same approach as abiword-plugin-clarisworks).
        # configure.ac carries no libtool macros (no LT_INIT /
        # AC_PROG_LIBTOOL, Makefile.am uses bin_PROGRAMS only), so
        # automake alone covers the bootstrap — no libtool needed.
        self.tool_requires("automake/1.18")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"lcs supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        # No tarball exists for SVN r738: fetch every pinned file from
        # its official !svn/bc/738 DAV URL into the source tree.  The
        # sha256 of each file was verified at conandata.yml creation.
        files = self.conan_data["sources"]["files"]
        for rel_path, meta in files.items():
            dst = os.path.join(self.source_folder, rel_path)
            os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
            download(self, meta["url"], dst, sha256=meta["sha256"])

    def generate(self):
        # Materialize the build environment (conanbuild script) so the
        # tool_requires above reach build(): automake's bin (aclocal,
        # automake) is prepended to PATH and its package_info exports
        # (ACLOCAL/AUTOMAKE, ACLOCAL_PATH, PERL5LIB) become visible.
        # build()'s self.run("autoreconf -fvi", env="conanbuild")
        # sources exactly this script.
        VirtualBuildEnv(self).generate()
        # NOTE: intentionally NOT using AutotoolsDeps.  It exports
        # LIBS=-lncursesw, which makes configure's AC_SEARCH_LIBS
        # resolve initscr as "none required", so neither USE_NCURSES
        # nor USE_NCURSES_W gets defined and includes.h #errors out.
        # Instead the dependency include/lib paths are added to the
        # toolchain env below (configure + make both see them) and the
        # library probe finds -lncursesw on its own.
        tc = AutotoolsToolchain(self)
        # AutotoolsToolchain does not inject dependency search paths
        # (that is AutotoolsDeps' job, which we cannot use here); add
        # the ncurses include/lib dirs to CPPFLAGS/LDFLAGS by hand.
        nc = self.dependencies["ncurses"]
        for inc in nc.cpp_info.includedirs:
            tc.extra_cxxflags.append(f"-I{inc}")
            tc.extra_cflags.append(f"-I{inc}")
        for lib in nc.cpp_info.libdirs:
            tc.extra_ldflags.append(f"-L{lib}")
        # Upstream is C++03-era code.  cursesgraphics.h initializes
        # int array members from chtype macros (ACS_BULLET etc., aka
        # unsigned int), which is ill-formed narrowing under C++11 and
        # later — a hard error with the profile's -std=c++17.  The
        # values are small non-negative acs constants, so disabling the
        # diagnostic restores the C++03 semantics the code was written
        # for (clang accepts -Wno-narrowing as an alias of
        # -Wno-c++11-narrowing).
        tc.extra_cxxflags.append("-Wno-narrowing")
        # shop.cpp uses std::mem_fun/not1 (C++03 binders, removed in
        # C++17).  libc++ keeps them behind the official escape hatch
        # _LIBCPP_ENABLE_CXX17_REMOVED_BINDERS; defining it restores
        # the C++03 semantics the code was written for, without
        # touching upstream source.
        tc.extra_cxxflags.append("-D_LIBCPP_ENABLE_CXX17_REMOVED_BINDERS")
        # Native build on HarmonyOS: build and host use the same profile
        # (ohos-aarch64), so AutotoolsToolchain passes no --build/--host
        # and configure falls back to running config.guess.  The
        # config.guess installed by autoreconf from automake/1.18
        # (timestamp 2024-07-27) does not recognize uname -s=HarmonyOS
        # and dies with "cannot guess build type; you must specify one".
        # Pass the build triplet explicitly (same approach as
        # bandwidthd/avr recipes): _get_gnu_triplet maps the build
        # profile's OHOS+armv8 to aarch64-linux-ohos, which the stock
        # config.sub that automake installs already accepts.
        build_triplet = _get_gnu_triplet(str(self.settings_build.os),
                                         str(self.settings_build.arch))["triplet"]
        tc.configure_args.append(f"--build={build_triplet}")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Bootstrap: upstream ships no configure script, only
        # configure.ac.  autoreconf -fvi regenerates it (plus the
        # Makefile.in's and config.h.in) before configure runs.
        self.run("autoreconf -fvi", cwd=self.source_folder, env="conanbuild")
        # E114: fix the temp-dir umask in the generated configure before
        # it runs (the CI host's old autoconf emits umask 077; the local
        # autoconf 2.72 emits umask 000; both are HMDFS-hostile).  Must
        # happen between autoreconf and configure so the patched block
        # also propagates into config.status.
        _fix_tmpdir_umask(os.path.join(self.source_folder, "configure"))
        autotools = Autotools(self)
        # Explicit --prefix: the OHOS-adapted conan injects --prefix=/
        # for cross builds, which bakes datadir=//share into the
        # compile-time INSTALL_DATA_DIR macro (src/Makefile.am) and
        # the installed binary then looks for its art data under
        # //share/lcs/art/.  Point configure at the real package
        # folder so INSTALL_DATA_DIR expands to <pkg>/share and the
        # binary finds <pkg>/share/lcs/art/ at runtime.
        autotools.configure(args=[f"--prefix={self.package_folder}"])
        autotools.make()
        # Upstream has no `make check` target (see notes.md); the
        # upstream "test" is running the game itself, which is done for
        # real in test_package via a PTY session.

    def package(self):
        autotools = Autotools(self)
        # prefix is already <package_folder> (see build()); pass
        # DESTDIR= so autotools.install() does not prepend a second
        # package_folder copy (files would land in <pkg>/storage/<pkg>).
        autotools.install(args=["DESTDIR="])

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        # Runtime data (art/*.cpc, xml, sitemaps.txt) installed to
        # share/lcs/art/, located by the binary via INSTALL_DATA_DIR.
        self.cpp_info.resdirs = ["share"]
        bin_dir = os.path.join(self.package_folder, "bin")
        self.runenv_info.prepend_path("PATH", bin_dir)
        # The binary links libc++_shared.so from the OHOS toolchain
        # (compiler.libcxx=libc++); surface that directory to consumers
        # through the run environment.
        libcxx_dir = "/storage/Users/currentUser/usr/local/lib/aarch64-linux-ohos"
        if os.path.isdir(libcxx_dir):
            self.runenv_info.append("LD_LIBRARY_PATH", libcxx_dir)
