#!/usr/bin/env python3
"""Conan recipe for catpoint 1.0.0 on HarmonyOS PC.

catpoint is a simple presenting software (terminal slideshow) by
bitreich: a ~290-line C program with an ncursesw UI.

Source: the official repo is served over git:// only (r-36.net /
git.2f30.org) — no HTTPS tarball exists, so we clone via the Git SCM
tool (git:// protocol verified reachable on host; falls back to https
git mirror). Version 1.0 is the release packaged by pkgsrc/bitreich.
"""
import os

from conan import ConanFile
from conan.tools.files import copy
from conan.tools.scm import Git
from conan.tools.env import Environment


class CatpointConan(ConanFile):
    name = "catpoint"
    version = "1.0.0"
    package_type = "application"
    license = "ISC"
    homepage = "https://git.2f30.org/catpoint"
    url = "https://git.2f30.org/catpoint"
    description = "Simple presenting software (terminal slideshow, ncursesw)"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires("ncurses/6.5")

    def source(self):
        git = Git(self)
        git.clone("git://r-36.net/catpoint", target=".")
        # fallback https mirror if git:// is blocked on CI
        if not os.path.isdir(os.path.join(self.source_folder, ".git")):
            git = Git(self)
            git.clone("https://git.2f30.org/catpoint", target=".")

    def build(self):
        # Makefile uses ${CC}/${CFLAGS}/${LDFLAGS} (CATPOINT_* = ${*});
        # pass them on the make command line (highest precedence — env
        # injection did not reach ${CPPFLAGS}: compile showed only
        # -D_DEFAULT_SOURCE, no -I, so curses.h was not found).
        ncurses = self.dependencies["ncurses"]
        self.run(
            "make "
            "CC=/data/service/hnp/bin/clang "
            f"CFLAGS='-O2 -I{ncurses.package_folder}/include' "
            f"LDFLAGS='-L{ncurses.package_folder}/lib -lncursesw'",
            cwd=self.source_folder,
        )

    def package(self):
        copy(self, "catpoint", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "catpoint.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.conf_info.define("user.catpoint:exe", os.path.join(
            self.package_folder, "bin", "catpoint"))
