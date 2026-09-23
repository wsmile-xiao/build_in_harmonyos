#!/usr/bin/env python3
"""Conan recipe for prover9 2017-11A (LADR-2017-11A).

Prover9/Mace4 — resolution/paramodulation first-order logic theorem prover
and finite model searcher (William McCune's LADR tool suite, continued by
Bob Veroff; this release line is carried by the ai4reason community repo).

Upstream has NO autoconf/configure: the build is a hand-written recursive
Makefile (ladr/ -> mace4.src/ -> provers.src/ -> apps.src/) that produces
a self-contained bin/ directory with 43 CLI tools.

Build notes (validated on OHOS aarch64):
  - `make all -j1 CC=<clang> XFLAGS="-fPIC -O2"` builds everything in ~11s.
  - -j1 is MANDATORY: -j2 triggers an upstream race between the recursive
    install targets (apps.src vs provers.src both move/cp into ../bin/),
    reported as `make[1]: *** [Makefile:47: install] Error 1`.
  - Zero third-party dependencies (pure C + libc; no readline/bison/flex).
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class Prover9Conan(ConanFile):
    name = "prover9"
    # Upstream release string is "2017-11A (CIIRC)" (LADR-2017-11A); the
    # conan version is the lowercased slug "2017-11a" (conan references
    # must be all lowercase — CI gate L0m-5, "must be all lowercase").
    version = "2017-11a"
    description = (
        "Prover9/Mace4 LADR tool suite: first-order logic + equational "
        "theorem prover and finite model searcher (43 CLI tools)"
    )
    license = "GPL-2.0"
    homepage = "https://github.com/ai4reason/Prover9"
    url = "https://github.com/ai4reason/Prover9"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"os={self.settings.os} is not supported"
            )

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler(self):
        # R33: compiler executable comes from the Conan profile conf, never
        # from a raw shell CC environment variable.
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = executables.get("c")
        if compiler:
            return compiler
        if cross_building(self):
            raise ConanInvalidConfiguration(
                "cross builds require tools.build:compiler_executables[c]"
            )
        return "cc"

    def build(self):
        apply_conandata_patches(self)
        compiler = self._compiler()
        # Upstream sub-Makefiles use `CFLAGS = $(XFLAGS) -O -Wall`, so extra
        # flags ride in through XFLAGS (validated: -fPIC -O2).
        # -j1 is mandatory: the recursive install targets race under -j2.
        # E002 (/tmp read-only on OHOS): upstream build writes no /tmp files,
        # temp paths come from the ambient TMPDIR set by the environment.
        self.run(
            f'make all -j1 CC="{compiler}" XFLAGS="-fPIC -O2"',
            cwd=self.source_folder,
            env=["conanbuild"],
        )
        # Upstream self-tests (L1c evidence, validated: all pass in ~3s):
        #   test1: prover9 proves a group-theory theorem, piped through
        #          prooftrans parents_only (16-step proof)
        #   test2: mace4 finds the 6-element noncommutative group model,
        #          piped through interpformat tabular
        #   test3: mace4 quasigroup enumeration piped through interpformat +
        #          isofilter (5 interpretations)
        self.run(
            "make test1 test2 test3",
            cwd=self.source_folder,
            env=["conanbuild"],
        )

    def package(self):
        copy(
            self,
            "COPYING",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        copy(
            self,
            "*",
            os.path.join(self.source_folder, "bin"),
            os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )
        if os.name != "nt":
            bin_dir = os.path.join(self.package_folder, "bin")
            for name in os.listdir(bin_dir):
                path = os.path.join(bin_dir, name)
                if os.path.isfile(path):
                    os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
