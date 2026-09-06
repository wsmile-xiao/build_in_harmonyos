#!/usr/bin/env python3
"""Conan recipe — npush 0.7 (ncurses logic game, single-file C++).

npush is a small terminal logic game similar to Sokoban / Boulder Dash,
written by David Richmond and distributed from the official SourceForge
project page (https://npush.sourceforge.net/).  It is a single-file C++
program (npush.cpp) with no configure script and no upstream test-suite.

OHOS adaptation notes:
- Depends on ncurses (provided by the conan package ncurses/6.4; wide-char
  static build -> link -lncursesw, header <ncurses.h> is shipped).
- Upstream Makefile hard-codes `g++` and `-lncurses` and has no install
  target, so we compile the single translation unit directly with the
  compiler from Conan conf (R33) and package the result ourselves.
- npush locates its level data in a `levels/` directory relative to the
  *current working directory* (opendir("levels")).  To keep the package
  relocatable we install the real binary + `levels/` under
  share/npush/ and ship a tiny POSIX launcher in bin/npush that cd's into
  that directory before exec (same pattern as Homebrew's npush formula).
- Source URL is the official SourceForge release tarball (R39) with a
  sha256 that was cross-verified against Homebrew / FreeBSD port records.
"""
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class NpushConan(ConanFile):
    name = "npush"
    version = "0.7"
    description = "npush - terminal logic game similar to Sokoban and Boulder Dash"
    license = "GPL-2.0-or-later"
    homepage = "https://npush.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("ncurses/6.4")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise Exception(f"npush {self.version} supports Linux/OHOS only (os={self.settings.os})")

    def source(self):
        # R39: official SourceForge URL + sha256 (CI adds mirror fallback)
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: compiler from Conan conf (never bare shell env vars)
        ce = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cxx = ce.get("cpp", "clang++")

        src = self.source_folder
        dep = self.dependencies["ncurses"]
        cpp_info = dep.cpp_info
        inc = ":".join(cpp_info.includedirs) if cpp_info.includedirs else os.path.join(dep.package_folder, "include")
        libdir = ":".join(cpp_info.libdirs) if cpp_info.libdirs else os.path.join(dep.package_folder, "lib")
        libs = " ".join(f"-l{lib}" for lib in cpp_info.libs)  # -> -lncursesw

        # Single translation unit, mirror upstream flags (upstream uses
        # -g -Wall; we use -O2 for a release build).
        self.run(
            f"{cxx} -O2 -Wall -DNDEBUG -I{inc} "
            f"{os.path.join(src, 'npush.cpp')} -L{libdir} {libs} "
            f"-o {os.path.join(self.build_folder, 'npush')}"
        )

    def package(self):
        # 1) real binary + level data under share/npush/
        copy(self, "npush",
             src=self.build_folder,
             dst=os.path.join(self.package_folder, "share", "npush"))
        copy(self, "*",
             src=os.path.join(self.source_folder, "levels"),
             dst=os.path.join(self.package_folder, "share", "npush", "levels"))
        copy(self, "readme.txt",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "npush"))
        copy(self, "COPYING",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "npush"))

        # 2) POSIX launcher in bin/ : cd into share/npush then exec (levels are
        #    resolved relative to cwd by the game). Homebrew uses the same trick.
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        launcher = os.path.join(bin_dir, "npush")
        with open(launcher, "w", encoding="utf-8") as fh:
            fh.write(
                "#!/bin/sh\n"
                "# npush launcher (conan package npush/0.7)\n"
                "SELF=\"$0\"\n"
                "DIR=$(CDPATH= cd -- \"$(dirname -- \"$SELF\")\" && pwd)\n"
                "cd \"$DIR/../share/npush\" || exit 1\n"
                "exec ./npush \"$@\"\n"
            )
        os.chmod(launcher, 0o755)
        os.chmod(os.path.join(self.package_folder, "share", "npush", "npush"), 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
