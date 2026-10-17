#!/usr/bin/env python3
"""Conan recipe - LBreakout2 2.6.5 (SDL 1.2 breakout game) for HarmonyOS PC.

Adaptation notes
================
* SDL 1.2 is supplied by sdl12-compat/1.2.68, which re-implements the SDL 1.2
  ABI on top of the published SDL2 runtime (the original SDL 1.2 tree does
  not build on OHOS).
* The vendored AM_PATH_SDL macro (acinclude.m4, 1999-era sdl.m4) discovers SDL
  exclusively through a `sdl-config` script:
    - without sdl-config on PATH configure hard-fails ("lib SDL is needed");
    - the sdl-config shipped inside the sdl12-compat package has the package
      builder's absolute prefix baked in, so its output points nowhere for
      any later build.
  The macro overwrites SDL_CFLAGS/SDL_LIBS from the sdl-config output, so
  merely exporting those variables does not help either. The recipe writes a
  tiny sdl-config shim into the build folder that reports the include/lib
  directories of the resolved sdl12-compat dependency and hands it to
  configure via SDL_CONFIG, which AC_PATH_PROG keeps when already set.
  --disable-sdltest keeps the bundled version-check program from being built;
  together with the explicit build/host triplets this pins the 2004-era
  configure into cross-compiling mode (no conftest execution).
* patches/0001-config.sub.patch teaches the vendored 2004 config.sub about
  aarch64 and linux-ohos; config.guess stays pristine because both triplets
  are passed explicitly.
* patches/0002-configure-umask.patch changes the config.status scratch
  directory umask 077 -> 022: HMDFS rejects the 0700 directories created by
  the old mktemp/mkdir fallback (knowledge E011, same fix as sdl-mixer).
* --disable-nls: the tarball bundles a 2004-era intl/ tree that is not
  cross-buildable with the OHOS toolchain; the game falls back to English.
* --disable-network: SDL_net 1.2 is not available in the archive set, which
  removes the client's NETWORK_ENABLED code paths. The standalone
  lbreakout2server socket daemon is still built and installed because
  upstream ships it unconditionally.
* Audio stays enabled: SDL_mixer 1.2.12 is linked and only plays WAV chunks;
  at runtime a failing Mix_OpenAudio is non-fatal (gui/stk.c keeps running
  with sound disabled).
* Upstream provides no test suite (no TESTS/check_PROGRAMS in any Makefile.am
  and no test directory); test_package/ runs the installed game headless
  through the SDL dummy drivers plus an SDL/SDL_mixer consumer runtime test.
"""
import os
import stat

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Lbreakout2Conan(ConanFile):
    name = "lbreakout2"
    version = "2.6.5"
    description = "LBreakout2 - breakout/arkanoid style arcade game for SDL 1.2"
    license = "GPL-2.0-or-later"
    homepage = "https://lgames.sourceforge.io/LBreakout2/"
    url = "https://sourceforge.net/projects/lgames/files/lbreakout2/"
    topics = ("sdl", "sdl1.2", "sdl12-compat", "game", "arcade", "breakout", "lgames", "ohos")
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("sdl12-compat/1.2.68")
        self.requires("sdl-mixer/1.2.12")
        self.requires("libpng/1.6.58")
        self.requires("zlib/1.3.1.1")

    def layout(self):
        basic_layout(self)
        # Build in-tree: the top-level lbreakout2.desktop rule reads
        # lbreakout2.desktop.in through a shell redirection, which ignores
        # the VPATH search of out-of-tree builds.
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        sdl_prefix = self.dependencies["sdl12-compat"].package_folder
        sdl_libdir = os.path.join(sdl_prefix, "lib")
        sdl_cflags = "-I{} -I{}".format(
            os.path.join(sdl_prefix, "include", "SDL"),
            os.path.join(sdl_prefix, "include"),
        )
        sdl_libs = "-L{} -Wl,-rpath-link,{} -lSDL-1.2".format(sdl_libdir, sdl_libdir)

        # AM_PATH_SDL only understands sdl-config; the copy inside the
        # sdl12-compat package has the package builder's prefix baked in, so
        # provide a shim reporting the dependency as resolved for this build.
        shim = os.path.join(self.build_folder, "sdl-config")
        with open(shim, "w", encoding="utf-8") as handle:
            handle.write("#!/bin/sh\n")
            handle.write('case "$1" in\n')
            handle.write('  --version) echo "1.2.68" ;;\n')
            handle.write('  --prefix|--exec-prefix) echo "{}" ;;\n'.format(sdl_prefix))
            handle.write('  --cflags) echo "{}" ;;\n'.format(sdl_cflags))
            handle.write('  --libs) echo "{}" ;;\n'.format(sdl_libs))
            handle.write('  *) echo "unsupported sdl-config option: $1" >&2; exit 1 ;;\n')
            handle.write("esac\n")
        os.chmod(shim, os.stat(shim).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        # LBreakout2 compiles SRC_DIR (game data, from --datadir) and HI_DIR
        # (highscore chart, from --localstatedir) into the binary, so the
        # prefix must be the final package folder itself instead of the
        # relocation-friendly "/" + DESTDIR scheme; package() therefore
        # installs with an explicit empty DESTDIR (same approach as the
        # abcm2ps recipe in this archive).
        tc = AutotoolsToolchain(self, prefix=self.package_folder)
        tc.configure_args.extend([
            # the bundled 2004 gettext/intl tree cannot be cross-built here
            "--disable-nls",
            # SDL_net 1.2 is not part of the archive set
            "--disable-network",
            # never compile/execute the bundled SDL version probe
            "--disable-sdltest",
            # AM_PATH_SDL discovers SDL only through sdl-config
            "SDL_CONFIG=" + shim,
        ])
        if self.settings.os == "OHOS":
            # State both triplets explicitly: the vendored 2004 config.guess
            # cannot identify the HarmonyOS build host, and the differing
            # build triplet pins autoconf into cross-compiling mode, which
            # skips its "can the compiler output be run" probe (it cannot
            # here: unsigned ELF) and the AM_GNU_GETTEXT runtime probes.
            tc.configure_args.extend([
                "--build=x86_64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-ohos",
            ])
        tc.generate()
        AutotoolsDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        # --prefix is already the package folder; an explicit empty DESTDIR
        # keeps the helper from re-rooting the install below it a second time.
        autotools.install(args=["DESTDIR="])
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
