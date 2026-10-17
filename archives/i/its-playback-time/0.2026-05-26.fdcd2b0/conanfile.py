#!/usr/bin/env python3
"""Conan recipe — its-playback-time 0.2026-05-26.fdcd2b0 (upstream program `ipbt`).

ipbt ("It's Playback Time") is Simon Tatham's curses-based player for
`ttyrec`-style terminal-session recordings: it embeds the PuTTY terminal
emulator, replays the recording through it and stores every resulting screen
state in an internal "movie" array, so a recording can be played forwards,
backwards, or jumped into at an arbitrary frame with equal ease.

Debian names the source package `its-playback-time` (maintainer Ian Jackson);
the upstream tarball and the programs it installs are `ipbt` (the player) and
`ipbt-dump` (a non-interactive converter that renders a recording as a hex
dump, as a typescript, or as XML describing each frame's screen).

Build system: CMake >= 3.10.  The tarball ships CMakeLists.txt + cmake/ and
has no configure script and no autotools files at all.

Build requirements actually used here:
  * ncurses wide character  -> Conan `ncurses/6.6`.  unix/CMakeLists.txt sets
    `CURSES_NEED_WIDE TRUE` before `find_package(Curses)`, i.e. upstream
    wants libncursesw, which is exactly what the ncurses/6.6 package ships
    (static, wide-char).
  * halibut                 -> OPTIONAL and deliberately NOT a Conan
    requirement.  doc/CMakeLists.txt only uses halibut to *re-generate* the
    roff man pages from man-*.but; making it a build requirement would force
    the build machine to execute an OHOS aarch64 halibut binary, which a
    cross build cannot do.  The tarball ships a pre-generated `ipbt.1`,
    which package() installs instead, so the man page still lands in the
    package.

No source patches are needed: the CMake build is plain portable C99, the only
external library is ncurses, and CMakeToolchain injects the OHOS compiler,
sysroot and static link flags.
"""

import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class ItsPlaybackTimeConan(ConanFile):
    name = "its-playback-time"
    version = "0.2026-05-26.fdcd2b0"
    description = (
        "ipbt - curses player for ttyrec terminal-session recordings "
        "(PuTTY-terminal-emulator based, by Simon Tatham)"
    )
    license = "MIT"
    homepage = "https://www.chiark.greenend.org.uk/~sgtatham/ipbt/"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # Two command-line tools (ipbt, ipbt-dump), no installable library.
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    _binaries = ("ipbt", "ipbt-dump")

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        # R32: the platform check must cover the OHOS target, never `== "Linux"`.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "its-playback-time supports Linux and OHOS, not "
                "{}".format(self.settings.os)
            )

    def requirements(self):
        self.requires("ncurses/6.6")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake >= 4 removed compatibility with the pre-3.5 policy set; harmless
        # on older CMake (halibut/1.3 precedent).
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # R26: this project only ever builds STATIC archives, and the ncurses
        # dependency is a static Conan package; pin it anyway so no system
        # -same-name .so can ever be produced or picked up.
        tc.variables["BUILD_SHARED_LIBS"] = False
        # The top-level CMakeLists.txt already does
        # `add_compile_definitions(HAVE_CMAKE_H NO_GSSAPI)`; setting
        # PUTTY_GSSAPI=OFF additionally stops cmake/platforms/unix.cmake from
        # probing for libdl / krb5-gssapi, neither of which exists on OHOS.
        tc.variables["PUTTY_GSSAPI"] = "OFF"
        # STRICT=ON turns -Wall into -Werror (upstream ships it OFF).
        tc.variables["STRICT"] = "OFF"
        # CMake's FindCurses locates its include directory with a bare
        # find_path(), and CMakeToolchain sets no CMAKE_FIND_ROOT_PATH here, so
        # the probe walks the BUILD MACHINE's /usr/include before it ever looks
        # at the ncurses package we depend on. On any machine that happens to
        # have system ncurses headers, FindCurses therefore reports
        # CURSES_HAVE_NCURSES_CURSES_H from `<host>/include/ncursesw/curses.h`
        # and unix/ipbt.c includes <ncursesw/curses.h>; on a machine without
        # them the same recipe fails with
        #   `fatal error: 'ncursesw/curses.h' file not found`
        # because the Conan ncurses package lays its headers out flat
        # (`include/ncurses.h`, no ncursesw/ subdirectory). So the outcome is
        # decided by the build host rather than by the dependency.
        # Point FindCurses at ncurses/6.6 itself: then
        # `${CURSES_INCLUDE_PATH}/ncursesw/curses.h` does not exist, all four
        # CURSES_HAVE_*_H stay false, and patch 0001 falls back to
        # <ncurses.h> out of that same directory. Pin the library for the same
        # reason - find_library() has no root-path guard either.
        ncurses = self.dependencies["ncurses"].cpp_info
        tc.cache_variables["CURSES_INCLUDE_PATH"] = ncurses.includedirs[0]
        tc.cache_variables["CURSES_LIBRARY"] = os.path.join(
            ncurses.libdirs[0], "libncursesw.a"
        )
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        built = os.path.join(self.build_folder, "ipbt")
        if not os.path.isfile(built):
            # upstream/CMakeLists.txt sets CMAKE_RUNTIME_OUTPUT_DIRECTORY to
            # ${CMAKE_BINARY_DIR}; fail loudly if that ever stops holding.
            raise ConanException(
                "CMake build finished but {} was not produced".format(built)
            )

        # Level-1 evidence: upstream ships no test suite whatsoever (audited;
        # see test_package/MANIFEST.yml upstream_test_audit). Report the
        # honest no_tests result instead of pretending ctest ran something.
        print(
            'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"cmake",'
            '"command":"ctest (not invoked: upstream defines no test target)",'
            '"discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0,'
            '"reason":"ipbt-20260527.fdcd2b0.tar.gz (sha256 5303c8010addf1b2'
            'dec5375c8cf32d70e1835545d639ee2183863e09d4e80aa3) contains no '
            'tests/ directory and no test sources; no CMakeLists.txt calls '
            'enable_testing()/add_test() or declares a test executable; the '
            'only *test* file in the tree is terminal/bidi_test.c, which no '
            'build rule references. Functional coverage is provided by '
            'test_package, which executes the packaged ipbt / ipbt-dump '
            'binaries."}',
            flush=True,
        )

    def package(self):
        cmake = CMake(self)
        cmake.install()

        # `cmake install` only installs a man page when doc/CMakeLists.txt
        # could regenerate it with halibut; since halibut is intentionally not
        # a build requirement, install the pre-generated roff page that the
        # tarball ships at the top level (produced upstream by halibut).
        manpage = os.path.join(self.source_folder, "ipbt.1")
        if os.path.isfile(manpage):
            copy(
                self,
                "ipbt.1",
                src=self.source_folder,
                dst=os.path.join(self.package_folder, "share", "man", "man1"),
            )

        copy(
            self,
            "LICENCE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        copy(
            self,
            "README",
            src=self.source_folder,
            dst=os.path.join(
                self.package_folder, "share", "doc", "its-playback-time"
            ),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        # libncursesw.a is linked statically into both binaries, but the
        # terminfo database is still needed at run time (initscr() reads it),
        # so keep ncurses in the consumer's cpp_info graph.
        #
        # Measured 2026-10-11 (Conan 2.29, profile ohos-aarch64-wsl): this line
        # alone does NOT forward TERMINFO / TERMINFO_DIRS into a consumer's
        # aggregated run environment - the ncurses node keeps run=False, so the
        # generated conanrunenv-*.sh carries no TERMINFO at all and the
        # dependency reports package_folder=None. A consumer that really needs
        # the terminal database has to declare it, e.g.
        #   self.requires("ncurses/6.6", run=True)
        # which is exactly what test_package/conanfile.py does.
        self.cpp_info.requires = ["ncurses::ncurses"]