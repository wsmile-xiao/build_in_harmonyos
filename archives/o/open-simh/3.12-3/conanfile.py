#!/usr/bin/env python3
"""Conan recipe for open-simh 3.12-3 (SIMH historical computer simulator suite).

Upstream is a pure GNU-make project (no configure).  The makefile builds a
common SCP core plus one executable per emulated machine; the default "all"
target builds 24 simulators (pdp1 pdp4 pdp7 pdp8 pdp9 pdp15 pdp11 pdp10 vax
vax780 nova eclipse i1401 i1620 altair gri i7094 id16 uc15 id32 sds lgp h316
sigma).  HarmonyOS adaptation notes:

* Cross toolchain: CC/AR are injected via make variables (GCC=clang …).
* Old-C compatibility: SIMH v3 relies on C "tentative definitions" (e.g.
  uint32 uc15_memsize; in pdp11_defs.h is *defined* in every including
  translation unit).  clang >= 15 defaults to -fno-common, so lld reports
  "duplicate symbol: uc15_memsize".  We add -fcommon to restore the
  pre-C99 behaviour expected by this 1993-2022 code base.
* Feature trimming for the OHOS target: NONETWORK=1 (no libpcap/ethernet,
  SIMH builds a stub eth simulator), TESTS=0 (v3.12-3 ships no tests/*.ini,
  the per-simulator RegisterSanityCheck hook finds nothing anyway), and
  video support is compiled out automatically because SIM_MAJOR==3.
* The upstream makefile has no "install" target; package() copies the
  built binaries from BIN/ into the package bin/ directory.
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout

# The 24 simulator executables produced by the upstream default "all" target.
SIMH_BINS = [
    "pdp1", "pdp4", "pdp7", "pdp8", "pdp9", "pdp15", "pdp11", "pdp10",
    "vax", "vax780", "nova", "eclipse", "i1401", "i1620", "altair", "gri",
    "i7094", "id16", "uc15", "id32", "sds", "lgp", "h316", "sigma",
]


class OpensimhConan(ConanFile):
    name = "open-simh"
    version = "3.12-3"
    description = (
        "SIMH historical computer simulator suite (open-simh v3.12-3): "
        "24 emulators for PDP-1/4/7/8/9/11/15, PDP-10, VAX/VAX780, NOVA, "
        "ECLIPSE, IBM 1401/1620/7094, Interdata 16/32b, UC15, SDS, LGP, "
        "H316, XDS Sigma, Altair and GRI-909."
    )
    license = "MIT"
    homepage = "https://github.com/open-simh/simh"
    url = "https://github.com/open-simh/simh"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        # Upstream makefile builds in the source tree (BIN/ output dir).
        self.folders.build = "."

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "open-simh/3.12-3 in this recipe is a HarmonyOS PC adaptation"
            )

    def source(self):
        get(
            self,
            url=self.conan_data["sources"]["url"],
            sha256=self.conan_data["sources"]["sha256"],
            strip_root=True,
        )

    def build(self):
        # No patches are currently needed for the OHOS build, but keep the
        # standard patch hook so future conandata patches apply cleanly.
        apply_conandata_patches(self)
        # tools.build:compiler_executables carries the OHOS cross toolchain
        # (see ci/conan/profiles/ohos-aarch64); never rely on bare $CC env.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang")
        self.run(
            "make -j1 GCC={} NONETWORK=1 TESTS=0 CFLAGS_G=-fcommon all".format(
                cc
            ),
            env="conanbuild",
        )

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        for exe in SIMH_BINS:
            src = os.path.join(self.build_folder, "BIN", exe)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(bindir, exe))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
