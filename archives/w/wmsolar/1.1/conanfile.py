#!/usr/bin/env python3
"""Conan recipe — wmsolar 1.1

Window Maker/X11 dockapp that renders a heliocentric view of the solar system
(at 90 degrees).  Pure C/C++ astronomy code (VSOP87/Lunar/Pluto/RiseSet) with
an X11 XPM-icon dockapp front-end.

Build system: hand-written Makefile (no configure).  ``make`` produces the
``wmSolar`` binary linking ``-lXpm -lX11 -lXext -lm``.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class WmsolarConan(ConanFile):
    name = "wmsolar"
    version = "1.1"
    description = "Window Maker dockapp showing the solar system (heliocentric view at 90 degrees)"
    license = "GPL-2.0"
    homepage = "https://github.com/engerim42/wmsolar"
    url = "https://github.com/engerim42/wmsolar"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libxpm/3.5.17")
        self.requires("libxext/6.4.0.1")

    def layout(self):
        basic_layout(self)

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: get compiler from Conan conf (never bare shell env vars)
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = comp_execs.get("cpp") or "clang++"

        # Collect include/lib dirs from the dependency graph and feed them into
        # the hand-written Makefile's INCDIR/LIBDIR variables (they are not
        # pkg-config aware; the upstream defaults point at /usr/X11R6).
        # NOTE: Conan 2 cpp_info.includedirs/libdirs are already absolute
        # paths (package_folder-relative), so do NOT re-prefix them.
        inc_dirs, lib_dirs = [], []
        for dep in self.dependencies.values():
            for inc in dep.cpp_info.includedirs:
                inc_dirs.append(f"-I{inc}")
            for ld in dep.cpp_info.libdirs:
                lib_dirs.append(f"-L{ld}")

        inc = " ".join(inc_dirs)
        libd = " ".join(lib_dirs)
        # R9: always -j1 (HMDFS make jobserver issue)
        # wmSolar.c/xutils.c are compiled by the same CC (C++ mode, legacy Makefile)
        self.run(
            f"make -j1 CC={cxx} INCDIR='{inc}' LIBDIR='{libd}' "
            f"LIBS='-lXpm -lX11 -lXext -lm'",
            cwd=self.source_folder,
        )

        # DarkCal: upstream console program (Makefile.astro) computing the
        # darkest hours of a month.  Pure astronomy math, no X11 dependency —
        # ships as a second executable and serves as a true end-to-end
        # consumer use case (run "DarkCal 9 2026" -> per-day computation table).
        for src in ("DarkCal.cpp", "ConfigFile.cpp"):
            self.run(
                f"{cxx} -O2 -ffast-math -c {src} -o {src.replace('.cpp', '.o')}",
                cwd=self.source_folder,
            )
        self.run(
            f"{cxx} -O2 -ffast-math -o DarkCal DarkCal.o ConfigFile.o "
            f"AstroOps.o DateOps.o DateOpsIntl.o PlanetData.o "
            f"Lunar.o Pluto.o MathOps.o RiseSet.o Vsop.o -lm",
            cwd=self.source_folder,
        )

    def package(self):
        # two executables: wmSolar (X11 dockapp) + DarkCal (console, no X)
        copy(self, "wmSolar", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "DarkCal", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # GUI dockapp, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]