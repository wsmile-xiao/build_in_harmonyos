#!/usr/bin/env python3
"""Conan recipe — bsd-games 3.3.

bsd-games 3.3: classic text-mode games from BSD folklore (18 games:
adventure, arithmetic, atc, battlestar, caesar, cribbage, dab, drop4,
gofish, gomoku, hangman, klondike, robots, sail, snake, spirhunt, worm,
wump).  Hand-written configure + make (no autoconf), depends on ncurses
for terminal UI.

OHOS adaptations:
- INSTALL_SCORE drops `-g users` (OHOS has no `users` group) — patch
  0001-Config.mk.in.patch
- The ncurses Conan package ships ncursesw.pc only; alias it as ncurses.pc
  (generators_folder, R49) so the configure pkg-config probe succeeds;
  otherwise the default `-lncurses` fallback fails to link against
  libncursesw.a.
"""

import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class BsdGamesConan(ConanFile):
    name = "bsd-games"
    version = "3.3"
    description = "bsd-games 3.3 — classic text mode games from BSD folklore"
    license = "BSD-3-Clause"
    homepage = "https://bsd-games.sourceforge.io/"
    url = "https://bsd-games.sourceforge.io/"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("ncurses/6.6")

    def validate(self):
        # R32: use `in ("Linux", "OHOS")` rather than `== "Linux"`
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"bsd-games supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # The ncurses Conan package ships only ncursesw.pc.  The configure
        # script probes `pkg-config ncurses`; alias ncurses.pc inside the
        # generators folder so the probe succeeds and injects -I/-L/-lncursesw.
        # AutotoolsToolchain already prepends generators_folder to
        # PKG_CONFIG_PATH, so a plain copy here is the reliable channel.
        # NB: ncursesw.pc uses `prefix=${pcfiledir}/../..` (relative), which
        # resolves to the build dir once copied here — rewrite it to the real
        # ncurses package folder so -I/-L point at the actual headers/libs.
        nc = self.dependencies["ncurses"]
        nc_pc_dir = os.path.join(nc.package_folder, "lib", "pkgconfig")
        src_pc = os.path.join(nc_pc_dir, "ncursesw.pc")
        dst_pc = os.path.join(self.generators_folder, "ncurses.pc")
        if os.path.isfile(src_pc) and not os.path.exists(dst_pc):
            with open(src_pc, encoding="utf-8") as f:
                content = f.read()
            content = content.replace(
                "${pcfiledir}/../..",
                nc.package_folder,
            )
            with open(dst_pc, "w", encoding="utf-8") as f:
                f.write(content)
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        prefix = shlex.quote(self.package_folder)
        localstate = shlex.quote(os.path.join(self.package_folder, "var", "lib"))
        self.run(
            f"./configure --prefix={prefix} --localstatedir={localstate}",
            cwd=self.source_folder,
            env="conanbuild",
        )
        self.run(
            "make -j1",
            cwd=self.source_folder,
            env="conanbuild",
        )

    def package(self):
        # configure --prefix=package_folder, so `make install` stays inside
        # the package: bin/, share/man/man6, var/lib/bsdgames/.
        self.run(
            "make install",
            cwd=self.source_folder,
            env="conanbuild",
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
