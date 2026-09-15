#!/usr/bin/env python3
"""Conan recipe — curseofwar 1.3.0 (hand-written Makefile).

Curse of War is a fast-paced action RTS game with an ncurses terminal UI.
Upstream ships a hand-written Makefile (default target builds the ncurses
frontend `curseofwar`; `SDL=yes` builds the SDL frontend, which is out of
scope here — the ncurses binary is the primary game). There is no
configure script and no check/test target.
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class CurseofwarConan(ConanFile):
    name = "curseofwar"
    version = "1.3.0"
    description = "Curse of War — fast-paced action real-time strategy game with ncurses UI"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/a-nikolaev/curseofwar"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # CLI game tool, not a library (R38: commands.json declared at
    # software level).
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        # R32: allow both Linux hosts and the OHOS target triplet.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "curseofwar supports Linux and OHOS, not {}".format(self.settings.os)
            )

    def requirements(self):
        # Upstream Makefile links LDLIBS += -lncurses; the ncurses/6.6
        # package ships the wide-char static lib (libncursesw.a).
        self.requires("ncurses/6.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        env = VirtualBuildEnv(self)
        env.generate()

    def build(self):
        apply_conandata_patches(self)
        # R33: the compiler comes from the Conan conf, never from a bare
        # shell $CC (empty on release workers -> silent miscompile). The
        # injected absolute path is validated because on some preflight
        # workers /data/service/hnp/bin/clang does not exist; fall back
        # to PATH lookup in that case (Error 127 otherwise).
        compiler_executables = self.conf.get("tools.build:compiler_executables",
                                             default={}, check_type=dict) or {}
        cc = compiler_executables.get("c") or os.environ.get("CC") or ""
        if not cc or (os.path.sep in cc and not os.path.isfile(cc)):
            cc = (
                shutil.which("clang")
                or shutil.which("cc")
                or shutil.which("gcc")
                or os.environ.get("CC")
                or "clang"
            )
        self.output.info("Using C compiler: {}".format(cc))

        ncurses_pkg = self.dependencies["ncurses"].package_folder
        ncurses_inc = os.path.join(ncurses_pkg, "include")
        ncurses_lib = os.path.join(ncurses_pkg, "lib")
        # Upstream links -lncurses, but ncurses/6.6 only provides
        # libncursesw.a. Create a libncurses.a symlink so -lncurses
        # resolves (dhex 0.69 / dialog 1.3-20240307 precedent).
        local_libs = os.path.join(self.build_folder, "curseofwar-local-libs")
        os.makedirs(local_libs, exist_ok=True)
        link_src = os.path.join(ncurses_lib, "libncursesw.a")
        link_dst = os.path.join(local_libs, "libncurses.a")
        if os.path.islink(link_dst) or os.path.exists(link_dst):
            os.remove(link_dst)
        os.symlink(link_src, link_dst)

        version = str(self.version)
        install_data = os.path.join(self.package_folder, "res", "curseofwar")
        # R9: single job — parallel make hits the HMDFS jobserver fifo.
        # Command-line overrides keep the upstream Makefile untouched:
        # CPPFLAGS carries the required -DVERSION / -DINSTALL_DATA macros
        # that the Makefile defines for itself but that we must supply
        # because we override the variable on the command line.
        # Quoting chain (verified on /system/bin/sh mksh + bash):
        #   self.run string -> bash:  CPPFLAGS="'...-DVERSION='\"1.3.0\"'"
        #   make var value:           -DVERSION='"1.3.0"'
        #   recipe shell (mksh):      strips ' -> clang sees -DVERSION="1.3.0"
        #   C code:                   #define VERSION "1.3.0"  (string literal)
        # The escaped \" inside the double-quoted make argument is what
        # keeps the quotes alive through all three layers; a bare \"\"
        # form dies on mksh with "no closing quote".
        cppflags = (
            "-I{inc} -DVERSION='\\\"{ver}\\\"' -DINSTALL_DATA='\\\"{data}/\\\"'".format(
                inc=ncurses_inc, ver=version, data=install_data
            )
        )
        self.run(
            'make -j1 CC="{cc}" CFLAGS="-O2 -Wall" CPPFLAGS="{cppflags}" '
            'LDFLAGS="-L{local_libs} -L{lib}" LDLIBS="-lncurses -lm"'.format(
                cc=cc, cppflags=cppflags, local_libs=local_libs, lib=ncurses_lib
            ),
            cwd=self.source_folder,
            env="conanbuild",
        )
        binary = os.path.join(self.source_folder, "curseofwar")
        if not os.path.isfile(binary):
            raise ConanException("curseofwar binary was not produced by make")

    def package(self):
        # Upstream `make install` hardcodes DESTDIR-style PREFIX=/usr and
        # installs man pages with gzip; install the binary and the docs
        # manually into the package folder instead.
        copy(self, "curseofwar", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "README", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", "curseofwar"),
             keep_path=False)
        copy(self, "CHANGELOG", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", "curseofwar"),
             keep_path=False)

    def package_info(self):
        # Standalone game binary, no library to link against. ncurses is
        # a *runtime* dependency of the shipped binary (terminfo database
        # + wide-char libcursesw static code already linked in), so declare
        # it via cpp_info.requires — this puts ncurses into the run graph
        # (self.dependencies["ncurses"].package_folder resolves in
        # consumers/test_package, and VirtualRunEnv forwards its
        # runenv_info exports: TERMINFO/TERMINFO_DIRS/PATH).
        self.cpp_info.requires = ["ncurses::ncurses"]
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
