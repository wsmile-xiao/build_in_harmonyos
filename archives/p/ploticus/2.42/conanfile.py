#!/usr/bin/env python3
"""Conan recipe — ploticus 2.42 (hand-written GNU Makefile project).

Ploticus is a command line data display engine: it renders charts and graphs
from scripts written in the ploticus language.  The upstream 2.42 tarball
contains no autotools/CMake machinery, only ``src/Makefile``, so the build is
driven with ``make`` directly.

Built configuration (upstream default, "Setting 2 / Option 1"):

* ``pl`` — the executable, built with the bundled GD16 rasterizer
  (``exetarget: plpng``), i.e. PS/EPS/SVG/SVGZ/PNG output.  PNG and SVGZ need
  ``libpng`` + ``zlib``; X11 and SWF output stay disabled (``-DNOX11``,
  ``-DNOSWF``), which is the upstream default and matches HarmonyOS PC, where
  no X11 server exists.
* ``libploticus.a`` + ``libploticus.h`` — the embedding API library
  (upstream ``libploticus-static`` target).
* ``share/ploticus/prefabs`` — the upstream prefab library.

OpenHarmony (HarmonyOS PC, aarch64) adaptation — see ``patches/``:

``0001-src-preliminaries.c.patch`` makes the scratch directory runtime
selectable.  Upstream copies the compile-time ``TMPDIR`` macro (``/tmp``) into
``TDH_tmpdir`` and never consults the environment, so on HarmonyOS PC — where
``/tmp`` is mounted read-only — every code path that needs a temporary file
fails, e.g. ``proc drawcommands`` with
``error 522: Cannot open draw commands file (/tmp/ploXXXXXX)``.
The patch resolves the directory as: ``$TMPDIR`` if it is usable, else the
compiled-in default, else the current working directory, and probes usability
by actually creating a file in the candidate directory (``access()`` is not
trustworthy on HMDFS).  It introduces no platform macro.
"""
import os
import shlex

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PloticusConan(ConanFile):
    name = "ploticus"
    version = "2.42"
    description = ("Ploticus data display engine - renders charts and graphs from "
                   "ploticus scripts; produces PS, EPS, SVG, SVGZ and PNG")
    license = "GPL-2.0-or-later"
    homepage = "https://ploticus.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # PNG output (bundled GD16) and compressed SVG need libpng + zlib.
        # zlib is a system-name library: the conan package ships libz.a only,
        # so it is linked statically (R26).
        self.requires("libpng/1.6.58.3")
        self.requires("zlib/1.3.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _make_flags(self):
        """Return (-I flags, -L flags) for the dependency headers/libraries.

        Every path is quoted, because the conan cache may live under a
        directory whose name contains blanks.
        """
        incs, libdirs = [], []
        for dep in ("libpng", "zlib"):
            cpp_info = self.dependencies[dep].cpp_info
            incs.extend(cpp_info.includedirs)
            libdirs.extend(cpp_info.libdirs)
        inc_flags = " ".join(f'-I"{d}"' for d in incs)
        lib_flags = " ".join(f'-L"{d}"' for d in libdirs)
        return inc_flags, lib_flags

    def build(self):
        apply_conandata_patches(self)

        # R33: take the compilers from the Conan profile, not from the shell
        # environment (which is empty on the CI workers).
        compilers = self.conf.get("tools.build:compiler_executables", default={},
                                  check_type=dict) or {}
        cc = compilers.get("c", "clang")
        ar = compilers.get("ar", "llvm-ar")

        inc_flags, lib_flags = self._make_flags()
        # src/Makefile variables: GD16H = -I flags for png.h/zlib.h,
        # GD16LIBS = -L flags plus -lpng -lz.
        gd16h = shlex.quote(inc_flags)
        gd16libs = shlex.quote(f"{lib_flags} -lpng -lz")
        common = f"CC={shlex.quote(cc)} GD16H={gd16h} GD16LIBS={gd16libs}"

        src = os.path.join(self.source_folder, "src")
        # Default target of src/Makefile (exetarget -> plpng) builds `pl`.
        self.run(f"make {common} -j1", cwd=src)
        # Upstream target for the embedding library.
        self.run(
            f"make {common} ARCOM={shlex.quote(ar + ' r')} LIBEXT=a "
            f"libploticus-static -j1",
            cwd=src,
        )

    def package(self):
        src = os.path.join(self.source_folder, "src")
        copy(self, "pl", src=src, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "libploticus.a", src=src, dst=os.path.join(self.package_folder, "lib"))
        copy(self, "libploticus.h", src=src, dst=os.path.join(self.package_folder, "include"))
        copy(self, "Copyright", src=src, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "GPL.txt", src=src, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "*", src=os.path.join(self.source_folder, "prefabs"),
             dst=os.path.join(self.package_folder, "share", "ploticus", "prefabs"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libs = ["ploticus"]
        # Ship the prefab library in the package and point PLOTICUS_PREFABS at
        # it, so `pl -prefab ...` works without manual environment setup.
        self.runenv_info.define_path(
            "PLOTICUS_PREFABS",
            os.path.join(self.package_folder, "share", "ploticus", "prefabs"),
        )
