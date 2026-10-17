#!/usr/bin/env python3
"""Conan recipe for cube2font 1.5.1 — Cube Engine 2 font bitmap generator.

cube2font turns a TrueType font into the assets Cube Engine 2 games (Red
Eclipse and derivatives) load at runtime: one or more PNG texture pages holding
the rendered character grid plus a plain-text .cfg file with the per-character
atlas coordinates. Characters are rendered through FreeType, optionally
stroked with an inner/outer border, packed into texture pages and written as
8-bit greyscale+alpha PNG files deflated with zlib.

Upstream ships no standalone cube2font release: the tool lives in the Red
Eclipse engine repository as src/shared/cube2font.c (556 lines, single
translation unit, no header of its own), so the recipe builds that file from
the v1.5.1 tag — the same revision Debian re-packs as cube2font 1.5.1-1.

OHOS adaptation:
- src/Makefile probes FreeType through the `freetype-config` helper, which
  FreeType removed in 2.9.1 and the Conan freetype package does not provide, so
  both the compile and the link rule failed with
  "freetype-config: inaccessible or not found" followed by
  "'ft2build.h' file not found". The patch switches those two rules to
  pkg-config against the freetype2 module emitted by PkgConfigDeps.
- src/Makefile derives PLATFORM from `gcc -dumpmachine`. The OHOS toolchain has
  no gcc, so the recipe passes the Conan host triplet explicitly instead of
  letting every reference re-run a failing shell probe.
- cube2font also needs zlib (PNG deflate). The OHOS zlib package is static-only
  and exposes no freetype-config equivalent, so its include/lib paths are passed
  through pkg-config --cflags/--libs for the zlib module.

The binary is dynamically linked against libfreetype.so.6 with no rpath: the
runtime library path comes from the Conan run environment (conanrun), as the
test_package conversion run demonstrates.
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class Cube2fontConan(ConanFile):
    name = "cube2font"
    version = "1.5.1"
    description = ("Cube Engine 2 font bitmap generator: renders a TrueType font "
                   "into PNG texture pages plus a .cfg atlas coordinate file")
    license = "Zlib"
    homepage = "https://www.redeclipse.net"
    url = "https://github.com/red-eclipse/base"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    generators = "PkgConfigDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("freetype/2.14.3")
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: settings.os must be checked, cube2font only ships for Unix-like targets
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name} only supports Linux and OHOS, not {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _cxx(self):
        # R33: compiler comes from the Conan conf, never from an undefined shell variable
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        return compilers.get("cpp") or compilers.get("c") or "clang++"

    def _pkg_config(self):
        configured = self.conf.get("tools.gnu:pkg_config", default=None, check_type=str)
        return configured or shutil.which("pkg-config") or "pkg-config"

    def _platform(self):
        """Upstream's PLATFORM probe (`gcc -dumpmachine`) cannot run here."""
        machine = {"armv8": "aarch64", "armv7": "armv7", "x86": "i686"}.get(
            str(self.settings.arch), str(self.settings.arch))
        return f"{machine}-unknown-linux-{str(self.settings.os).lower()}"

    def build(self):
        apply_conandata_patches(self)

        # PkgConfigDeps wrote freetype2.pc and zlib.pc into the generators folder
        os.environ["PKG_CONFIG_PATH"] = self.generators_folder
        pkg_config = self._pkg_config()

        # Passing CXXFLAGS on the make command line replaces upstream's own
        # assignment (src/Makefile line 6), so restate it: Release keeps
        # upstream's optimisation profile, Debug builds unoptimised with -g.
        if str(self.settings.build_type) == "Release":
            opt = "-O3 -fomit-frame-pointer -ffast-math"
        else:
            opt = "-O0 -g"

        # Only the cube2font target is built: the default `all` target pulls the
        # SDL/X11 client and the enet server, which this package does not ship.
        self.run(
            f'make -j1 cube2font '
            f'PLATFORM={self._platform()} '
            f'CXX={self._cxx()} '
            f'PKG_CONFIG={pkg_config} '
            f'CXXFLAGS="$({pkg_config} --cflags zlib) {opt}" '
            f'LDFLAGS="$({pkg_config} --libs zlib)"',
            env="conanbuild",
            cwd=os.path.join(self.source_folder, "src"),
        )

    def package(self):
        copy(self, "cube2font",
             src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "cube2font.1",
             src=os.path.join(self.source_folder, "doc", "man"),
             dst=os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "license.txt",
             src=os.path.join(self.source_folder, "doc"),
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
