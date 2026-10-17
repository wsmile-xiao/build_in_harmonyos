#!/usr/bin/env python3
"""Conan recipe — pla 1.3 (Makefile project, cairo-based Gantt chart generator).

pla is a command-line tool that turns a simple task description file into a
Gantt chart. It renders through cairo and can emit PNG / EPS / PDF / SVG.

Build notes:
  - pla ships a plain Makefile (no configure). It discovers cairo through
    `pkg-config --cflags/--libs cairo` (Makefile variable PKG_CONFIG).
  - `PkgConfigDeps` is generated so cairo's .pc (plus pixman-1 / libpng /
    fontconfig / freetype2 / expat) is visible under PKG_CONFIG_PATH.
  - R33: the compiler path is read from Conan conf, never from a bare
    `${CC}` shell variable. LD_LIBRARY_PATH is neutralised during build to
    keep the host /usr/local/lib (which contains a conflicting libxml2) from
    shadowing the OHOS SDK's lld (E132).
  - Package type is "application": the artifact is the `pla` executable in
    bin/, so `commands.json` (R38) is provided at the software level.
"""

import os
import shutil

from conan import ConanFile
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class PlaConan(ConanFile):
    name = "pla"
    version = "1.3"
    description = ("Generate Gantt charts from a task description file "
                   "(outputs PNG/EPS/PDF/SVG through cairo)")
    license = "GPL-2.0-only"
    homepage = "https://www.arpalert.org/pla.html"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # cairo is the only third-party dependency (R36: already published).
        self.requires("cairo/1.18.4")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Make cairo (and its closure) discoverable for `pkg-config` by
        # writing cairo.pc / pixman-1.pc / ... into the generators folder.
        deps = PkgConfigDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        # R33: compiler path comes from Conan conf, not from ${CC}.
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        pkg_config = shutil.which("pkg-config") or "pkg-config"
        # Values below are injected from the Conan context (deterministic).
        #   - PKG_CONFIG_PATH points at the generated cairo .pc files.
        #   - LD_LIBRARY_PATH is cleared so the polluted host /usr/local/lib
        #     (a conflicting libxml2) cannot shadow the OHOS SDK's lld (E132).
        # pla's Makefile uses PKG_CONFIG for `pkg-config --cflags/--libs cairo`.
        cmd = (
            f"export PKG_CONFIG_PATH='{self.generators_folder}'; "
            "unset LD_LIBRARY_PATH; "
            f"make -C '{self.source_folder}' pla "
            f"CC='{cc}' PKG_CONFIG='{pkg_config}' -j1"
        )
        self.run(cmd, env="conanbuild")

    def package(self):
        # Command-line tool: install the pla executable to bin/.
        copy(self, "pla",
             src=os.path.join(self.source_folder),
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "COPYING",
             src=os.path.join(self.source_folder),
             dst=os.path.join(self.package_folder, "share", "doc", "pla"))

    def package_info(self):
        # Application package: no libraries/headers to propagate.
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.output.info("pla executable installed to bin/")
