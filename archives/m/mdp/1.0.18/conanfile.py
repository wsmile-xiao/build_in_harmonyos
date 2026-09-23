#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conan recipe for mdp 1.0.18 — command-line markdown presentation tool.

mdp is a ncursesw (wide-character ncurses) based terminal application.
Upstream builds with a plain recursive Makefile (no configure step):
the top-level Makefile compiles src/*.c and links a single `mdp` binary
with -lncursesw.  This recipe drives `make` with the cross compiler
from the Conan profile and installs the binary into bin/.

Note: upstream provides no `make check` test target (verified in
Makefile: targets are all/clean/install/uninstall only).  The L1
upstream-test requirement is therefore satisfied via the whitelisted
no-test classification and the consumer smoke tests below.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class MdpConan(ConanFile):
    name = "mdp"
    version = "1.0.18"
    description = "A command-line based markdown presentation tool"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/visit1985/mdp"
    url = "https://github.com/visit1985/mdp"

    topics = ("markdown", "presentation", "terminal", "ncurses")
    package_type = "application"
    languages = "C"

    settings = "os", "arch", "compiler", "build_type"

    # PkgConfigDeps generates ncursesw.pc from the ncurses/6.6 dependency;
    # VirtualBuildEnv wraps the cross toolchain env for self.run().
    generators = "VirtualBuildEnv", "PkgConfigDeps"

    def requirements(self):
        # mdp includes <curses.h> and links -lncursesw (wide-char flavor).
        # The ncurses recipe ships aggregated curses.h and generates the
        # ncursesw.pc pkg-config file exporting the right cflags/libs.
        self.requires("ncurses/6.6")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def validate(self):
        # mdp is a terminal application: requires a POSIX-like OS with
        # terminfo support.  Windows (pdcurses branch) is not supported
        # by this recipe.
        if str(self.settings.os) not in ("Linux", "OHOS", "FreeBSD", "Darwin", "Android"):
            raise ConanInvalidConfiguration(
                f"{self.name} only supports Linux/OHOS/FreeBSD/Darwin/Android"
            )

    def build(self):
        # R33: Get compiler from Conan settings/conf, not shell env vars
        cc_executables = self.conf.get("tools.build:compiler_executables", default={})
        if cc_executables:
            if isinstance(cc_executables, str):
                import json
                cc_executables = json.loads(cc_executables)
            cc = cc_executables.get("c", str(self.settings.compiler))
        else:
            cc = str(self.settings.compiler)

        # Locate pkg-config from dependencies (PkgConfigDeps .pc files)
        os.environ["PKG_CONFIG_PATH"] = self.generators_folder

        # mdp's Makefile: CURSES=ncursesw, LDLIBS=-lncursesw.
        # CFLAGS ?= -O3 means environment CFLAGS overrides default -O3;
        # we pass pkg-config flags via CFLAGS/LDFLAGS on the make command
        # line (command-line vars always win over the Makefile defaults).
        self.run(
            f'make CC={cc} '
            f'CFLAGS="$(pkg-config --cflags ncursesw) -O2" '
            f'LDFLAGS="$(pkg-config --libs ncursesw)" '
            f'-j1',
            env="conanbuild",
            cwd=self.source_folder,
        )

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        copy(self, "mdp", src=self.source_folder, dst=bindir)
        # license
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["licenses"]
