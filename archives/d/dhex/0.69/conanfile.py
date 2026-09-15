#!/usr/bin/env python3
"""Conan recipe — dhex 0.69 (Makefile).

dhex is an ncurses based hex editor featuring a diff mode. Upstream ships
a hand-written Makefile (targets: all/dhex/install/clean, no check/test
target) and builds a single `dhex` binary plus man pages.
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class DhexConan(ConanFile):
    name = "dhex"
    version = "0.69"
    description = "Ncurses based advanced hex editor featuring diff mode"
    license = "GPL-2.0-or-later"
    homepage = "https://www.dettus.net/dhex/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # CLI tool, not a library (R38: commands.json declared at software level)
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "dhex supports Linux and OHOS, not {}".format(self.settings.os)
            )

    def requirements(self):
        # Upstream Makefile links LIBS=-lncurses; the ncurses/6.6 package
        # ships the wide-char static lib (libncursesw.a).
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
        # R33: compiler comes from the Conan conf, never from a bare
        # shell $CC (empty on release workers -> silent miscompile).
        # The injected absolute path is validated: on some preflight
        # workers /data/service/hnp/bin/clang does not exist, so a
        # missing path must fall back to PATH lookup instead of being
        # passed blindly to make (Error 127).
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
        # libncursesw.a. Symlink so -lncurses resolves
        # (dialog/1.3-20240307 precedent on the same toolchain).
        local_libs = os.path.join(self.build_folder, "dhex-local-libs")
        os.makedirs(local_libs, exist_ok=True)
        link_src = os.path.join(ncurses_lib, "libncursesw.a")
        link_dst = os.path.join(local_libs, "libncurses.a")
        if os.path.islink(link_dst) or os.path.exists(link_dst):
            os.remove(link_dst)
        os.symlink(link_src, link_dst)
        # R9: single job — parallel make hits the HMDFS jobserver fifo.
        # Command-line overrides keep the hand-written Makefile untouched.
        self.run(
            "make -j1 CC={cc} CFLAGS=-O3\\ -Wall CPPFLAGS=-I{inc} "
            "LDFLAGS=-L{local_libs}\\ -L{lib} LIBS=-lncurses".format(
                cc=cc, inc=ncurses_inc, local_libs=local_libs, lib=ncurses_lib
            ),
            cwd=self.source_folder,
            env="conanbuild",
        )
        binary = os.path.join(self.source_folder, "dhex")
        if not os.path.isfile(binary):
            raise ConanException("dhex binary was not produced by make")

    def package(self):
        # Upstream `make install` hardcodes DESTDIR=/usr/local plus a
        # `strip` step, so install manually into the package folder.
        copy(self, "dhex", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(
            self,
            "dhex.1",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "man", "man1"),
        )
        for page in ("dhexrc.5", "dhex_markers.5", "dhex_searchlog.5"):
            copy(
                self,
                page,
                src=self.source_folder,
                dst=os.path.join(self.package_folder, "share", "man", "man5"),
            )

    def package_info(self):
        # Standalone binary, no library to link against
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
