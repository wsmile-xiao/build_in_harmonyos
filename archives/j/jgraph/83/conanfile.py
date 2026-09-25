#!/usr/bin/env python3
"""Conan recipe for jgraph 83 (plain POSIX makefile, 1997 K&R C).

jgraph is Jim Plank's filter that reads a graph description and writes a
PostScript file to standard output; it is the plotting engine used by many
LaTeX/documentation workflows (the upstream page ships a gallery of example
inputs and their PostScript output).

Upstream build: `make` -> ./jgraph (single binary; libc + libm only).

Adaptation notes (HarmonyOS PC / aarch64, OHOS SDK clang 15):
    * W0: no third-party dependencies (`requirements()` is intentionally
      absent — ANSI C plus POSIX only).
    * Ten portability patches under patches/ (see conandata.yml and
      notes.md).  The 1997 sources predate C99 and the 64-bit AArch64 ABI;
      the modernisations mirror what upstream itself did in revisions
      8.4-8.6 and what Debian carries in its 83-26 packaging: real `void`
      procedures, real declarations for the pointer-returning list
      primitives, and unconditional standard headers.
    * Upstream ships no test suite (no tests/ directory and no check/test
      target in the makefile — see test_package/MANIFEST.yml).  The
      consumer suite in test_package/ therefore exercises the installed
      binary itself (render, -p show mode, landscape translate, EPS
      bounding box, multi-page and error paths).
    * R33: the compiler comes from the Conan profile conf
      (tools.build:compiler_executables:c), never from a shell variable.

Artifacts: bin/jgraph, share/man/man1/jgraph.1 (software-level
commands.json declares the CLI, R38).  License: GPL-2.0-or-later.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    chdir,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class JgraphConan(ConanFile):
    name = "jgraph"
    version = "83"
    description = "Filter that turns a graph description into PostScript output"
    license = "GPL-2.0-or-later"
    homepage = "https://web.eecs.utk.edu/~jplank/plank/jgraph/jgraph.html"
    url = "https://web.eecs.utk.edu/~jplank/plank/jgraph/jgraph.html"
    topics = ("graph", "postscript", "plot", "cli")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: OHOS must be accepted next to Linux
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "jgraph only supports POSIX/Linux-family targets, not {0}".format(
                    self.settings.os
                )
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: compiler path comes from the Conan profile, not the shell env.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang") if compilers else "clang"
        with chdir(self, self.source_folder):
            # R9: keep the build serial.
            self.run('make -j1 CC="{0}"'.format(cc))

    def package(self):
        copy(
            self,
            "README",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        copy(
            self,
            "jgraph",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "bin"),
        )
        copy(
            self,
            "jgraph.1",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "man", "man1"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
