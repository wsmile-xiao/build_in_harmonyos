#!/usr/bin/env python3
"""Conan recipe — paml (Phylogenetic Analysis by Maximum Likelihood).

Upstream: https://github.com/abacus-gene/paml
Build system: plain Makefile in the src/ subdirectory (no configure, no
install target). The GitHub tag tarball extracts to {LICENSE, README.md,
dat, doc, examples, Technical, src/}.

Notes:
- `make clean` runs before compiling so no stale object/binary from a
  previous host build is ever reused (the v4.10.10 tag tarball itself ships
  no .o files, but the official abacus.gene mirror layout has hosted
  prebuilt artifacts before, so this is a defensive invariant).
- No library is produced: the package only ships CLI tools (baseml, codeml,
  evolver, mcmctree, pamp, yn00, chi2, ds, basemlg, infinitesites).
- R33: compiler comes from the conan profile conf, never from shell vars.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PamlConan(ConanFile):
    name = "paml"
    version = "4.10.10"
    description = "Phylogenetic Analysis by Maximum Likelihood (PAML suite: codeml, baseml, mcmctree, ...)"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/abacus-gene/paml"
    url = "https://github.com/abacus-gene/paml"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    # R32: OHOS platform compatibility — only Linux/OHOS hosts are supported.
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"paml requires a POSIX host (Linux or OHOS), got: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        # The codeload URL has no file extension; an explicit filename is
        # required so conan detects the archive format (.tar.gz).
        get(self, **self.conan_data["sources"],
            filename="paml-4.10.10.tar.gz", strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: compiler from profile conf ({"c": ..., "cpp": ...})
        comp = self.conf.get("tools.build:compiler_executables", check_type=dict, default={})
        cc = comp.get("c", "clang")

        # The GitHub tag tarball extracts to {LICENSE, README.md, dat, doc,
        # examples, Technical, src/}; the Makefile and all sources are in src/.
        src = os.path.join(self.source_folder, "src")
        self.run("make clean", cwd=src)
        # -j1: the upstream Makefile has no jobserver/parallel safety for the
        # shared tools.o rule (multiple programs depend on it); OHOS HMDFS
        # also lacks mkfifo, so a parallel make jobserver would fail anyway.
        self.run(
            "make -j1 CC={} CFLAGS='-O2 -Wall -Wno-unused-variable -Wno-unused-result -fPIC'".format(cc),
            cwd=src,
        )

    def package(self):
        src = os.path.join(self.source_folder, "src")
        dst = os.path.join(self.package_folder, "bin")
        os.makedirs(dst, exist_ok=True)
        binaries = [
            "baseml", "basemlg", "codeml", "evolver", "pamp",
            "yn00", "mcmctree", "infinitesites", "chi2", "ds",
        ]
        for binary in binaries:
            copy(self, binary, src=src, dst=dst)
            # make output can carry an odd mode; HMDFS/HAP enforces 0755.
            os.chmod(os.path.join(dst, binary), 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
