#!/usr/bin/env python3
"""Conan recipe for mmc 1.0 — Mesh-based Monte Carlo (MMC) photon transport simulator.

Upstream: https://github.com/fangq/mmc  (tag v1.0 = "MMC 1.0 Final (v2018 - Sachima)")
Build system: GNU make (src/Makefile + commons/Makefile_common.mk) — not autotools/cmake.
Produces the `mmc` command line executable under src/bin/.

Adapted for HarmonyOS / OpenHarmony (aarch64-unknown-linux-ohos, clang + musl libc):
  * upstream .DEFAULT_GOAL is `sse`, which injects x86-only `-msse4`/`-DMMC_USE_SSE`
    (src/simpmesh.h then pulls in <smmintrin.h>) -> unusable on aarch64; the `release`
    target documented in README.txt ("make release  # create a single-threaded
    optimized binary") is used instead. The resulting binary only needs libc.so.
  * patches/0001 ports the sources to clang/musl (__builtin_sincosf, BSD `uint`).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class MmcConan(ConanFile):
    name = "mmc"
    version = "1.0"
    description = "Mesh-based Monte Carlo (MMC) — 3D photon transport simulator on tetrahedral meshes"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/fangq/mmc"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os check must use in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"mmc supports Linux and OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: take the compiler from the Conan toolchain, never from bare shell vars.
        # The upstream Makefile hardcodes `CXX := g++`, so CXX/CC must be overridden
        # on the make command line.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        cxx = compilers.get("cpp", "clang++") if compilers else "clang++"

        # `release` = upstream-documented non-SSE build (-O3, single threaded).
        # `sse`/`ssemath` (upstream default) need x86 SSE4 intrinsics; the `omp`
        # variant links a build-machine RUNPATH to libomp -> not relocatable.
        # USERCCFLAGS appends -g0: the upstream Makefile always adds -g, and DWARF
        # would otherwise embed the build-machine absolute path in the binary.
        # (Do NOT strip afterwards: OHOS only executes signed ELFs, and stripping
        # invalidates the signature -> "operation not permitted".)
        self.run(f"make CC={cc} CXX={cxx} USERCCFLAGS='-DUSE_OS_TIMER -g0' -j1 release",
                 cwd=os.path.join(self.source_folder, "src"))

    def package(self):
        copy(self, "mmc", os.path.join(self.source_folder, "src", "bin"),
             os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE.txt", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
