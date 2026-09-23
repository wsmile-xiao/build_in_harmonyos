#!/usr/bin/env python3
"""Conan recipe for CodonW 1.4.4 — plain-Makefile command-line tool.

Upstream has no install target; the Makefile `links` target creates
per-analysis argv[0] aliases with hard links, which HMDFS forbids
(knowledge E079) — the platform patch swaps `ln -f` for `cp -f`.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class CodonwConan(ConanFile):
    name = "codonw"
    version = "1.4.4"
    description = "CodonW: codon usage analysis package (CAI/FOP/CBI/ENC/GC/RSCU/COA)"
    license = "GPL-2.0-only"
    homepage = "http://codonw.sourceforge.net"
    url = "https://sourceforge.net/projects/codonw/"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # per-analysis argv[0] variants built by the upstream `links` target
    _links = ("rscu", "cu", "aau", "raau", "tidy", "reader", "cutab",
              "cutot", "transl", "bases", "base3s", "dinuc", "cai",
              "fop", "gc3s", "gc", "cbi", "enc")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "codonw is supported only on Linux/OHOS")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("c", "cc")
        # HMDFS forbids hard links (knowledge E079): override the Makefile's
        # LN for the argv[0] alias `links` target instead of patching it,
        # which also avoids colliding with the tarball's own Makefile.orig
        self.run(f'make -C "{self.source_folder}" all CC="{cc}" LN="cp -f"')

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        for name in ("codonw",) + self._links:
            copy(self, name, src=self.source_folder, dst=bindir)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH",
                                      os.path.join(self.package_folder, "bin"))
