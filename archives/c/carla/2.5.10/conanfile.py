#!/usr/bin/env python3
"""Conan recipe for Carla 2.5.10 — audio plugin host (Makefile project).

Carla is a fully-featured audio plugin host with support for many audio
drivers and plugin formats. It builds with a plain GNU Make setup.

HarmonyOS adaptation notes:
  - clang does not recognise the GCC-only `-fno-gnu-unique` flag; patch
    0001 drops it from source/Makefile.mk.
  - musl does not provide <fts.h>; patch 0002 rewrites
    ysfx_utils_fts.cpp to use POSIX nftw instead.

The build has no required dependencies; all audio/GUI drivers are
optional and are simply not detected by pkg-config on HarmonyOS.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class CarlaConan(ConanFile):
    name = "carla"
    version = "2.5.10"
    description = "Carla — fully-featured audio plugin host"
    license = "GPL-2.0-or-later"
    homepage = "https://kx.studio/Applications:Carla"
    url = ""

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "with_qt": [True, False]}
    default_options = {"shared": True, "with_qt": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def source(self):
        # Offline-friendly: if the upstream URL cannot be reached (CI sandboxes
        # that proxy via a mirror, or local no-network runs), fall back to a
        # tarball supplied through the CARLA_LOCAL_TARBALL env var. The local
        # tarball path performs an explicit check_sha256() against
        # conandata.yml before unzipping, so an upstream or network mirror
        # serving a tampered tarball still fails the recipe.
        src_meta = self.conan_data["sources"]
        local_tar = os.environ.get("CARLA_LOCAL_TARBALL")
        if local_tar and os.path.isfile(local_tar):
            from conan.tools.files import unzip, check_sha256
            check_sha256(self, local_tar, src_meta["sha256"])
            unzip(self, local_tar, destination=self.source_folder, strip_root=True)
            self.output.info(f"Used local tarball {local_tar} for {src_meta['url']}")
        else:
            get(self, **src_meta, strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # Carla's Makefile.deps.mk defaults CC=gcc/CXX=g++ but the
        # HarmonyOS toolchain is clang. Conan's profile injects its own
        # CC/CXX into the environment; the Makefile's `CC ?= gcc` is meant
        # to be overridden by the environment, but Conan's injected value
        # points at a path that doesn't exist on this host. Pass CC/CXX on
        # the make command line (command-line args beat both env and `?=`).
        cc = self._cc()
        cxx = self._cxx()
        src = self.source_folder

        # Build the full host (backend + bridges + plugin + frontend core).
        self.run(f"make -j1 CC={cc} CXX={cxx}", cwd=src)

    def package(self):
        src = self.source_folder
        pkg = self.package_folder

        # Directories the upstream `make install` creates.
        for d in ("bin", "lib/carla", "lib/pkgconfig",
                  "include/carla/includes", "include/carla/utils",
                  "share/carla/resources"):
            os.makedirs(os.path.join(pkg, d), exist_ok=True)

        # 1. carla-single launcher (Python script) → bin/
        copy(self, "carla-single", os.path.join(src, "data"),
             os.path.join(pkg, "bin"))

        # 2. Backend shared libraries → lib/carla/
        copy(self, "libcarla_*", os.path.join(src, "bin"),
             os.path.join(pkg, "lib", "carla"))

        # 3. Bridge / discovery binaries → lib/carla/
        copy(self, "carla-bridge-*", os.path.join(src, "bin"),
             os.path.join(pkg, "lib", "carla"))
        copy(self, "carla-discovery-*", os.path.join(src, "bin"),
             os.path.join(pkg, "lib", "carla"))

        # 4. pkg-config files → lib/pkgconfig/
        copy(self, "*.pc", os.path.join(src, "data", "pkgconfig"),
             os.path.join(pkg, "lib", "pkgconfig"))

        # 5. Public headers → include/carla/
        copy(self, "*.h", os.path.join(src, "source", "includes"),
             os.path.join(pkg, "include", "carla", "includes"))
        copy(self, "*.h", os.path.join(src, "source", "utils"),
             os.path.join(pkg, "include", "carla", "utils"))

        # 6. Resources → share/carla/resources/
        copy(self, "*", os.path.join(src, "resources"),
             os.path.join(pkg, "share", "carla", "resources"))

        # Fix X-PREFIX-X placeholders in carla-single (upstream sed step)
        single = os.path.join(pkg, "bin", "carla-single")
        if os.path.isfile(single):
            with open(single, "r", encoding="utf-8") as f:
                content = f.read()
            content = content.replace("X-PREFIX-X", pkg)
            with open(single, "w", encoding="utf-8") as f:
                f.write(content)

        # Fix pkg-config X-PREFIX-X / X-LIBDIR-X / X-INCLUDEDIR-X / VERSION
        for pc in os.listdir(os.path.join(pkg, "lib", "pkgconfig")):
            pc_path = os.path.join(pkg, "lib", "pkgconfig", pc)
            if not os.path.isfile(pc_path):
                continue
            with open(pc_path, "r", encoding="utf-8") as f:
                content = f.read()
            content = content.replace("X-PREFIX-X", pkg)
            content = content.replace("X-LIBDIR-X", os.path.join(pkg, "lib"))
            content = content.replace("X-INCLUDEDIR-X",
                                      os.path.join(pkg, "include"))
            content = content.replace("VERSION", self.version)
            with open(pc_path, "w", encoding="utf-8") as f:
                f.write(content)

    def package_info(self):
        self.cpp_info.bindirs = ["bin", "lib/carla"]
        self.cpp_info.libdirs = ["lib/carla"]
        self.cpp_info.includedirs = ["include/carla/includes",
                                     "include/carla/utils"]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _cc(self):
        # Prefer the Conan-configured C compiler; fall back to clang.
        cc = os.environ.get("CC")
        if cc and shutil.which(cc):
            return cc
        return "clang"

    def _cxx(self):
        cxx = os.environ.get("CXX")
        if cxx and shutil.which(cxx):
            return cxx
        return "clang++"
