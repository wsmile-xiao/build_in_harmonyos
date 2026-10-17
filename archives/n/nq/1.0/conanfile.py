#!/usr/bin/env python3
"""Conan recipe for nq 1.0 — lightweight Unix job queue (nq/nqtail/nqterm).

nq is a set of small POSIX utilities (C + flock(2)) providing a zero-setup,
per-directory job queue.  Upstream uses a plain Makefile (no configure):

    * make            — builds `nq` and `nqtail` from nq.c/nqtail.c
                        (`nqterm` is a pre-existing shell script)
    * make check      — prove -v ./tests  (36 TAP assertions; runs real jobs)
    * make install    — installs binaries + man pages (needs `install`(1))

Adaptation notes (HarmonyOS PC, aarch64):
    * No third-party dependencies (W0: no requires).  Pure POSIX + flock(2).
    * Compiler comes from Conan conf (tools.build:compiler_executables:c),
      never from a bare shell variable (R33).
    * The upstream `install` target relies on the `install`(1) binary which is
      not guaranteed to be on PATH in the CI build environment; package()
      therefore does a direct copy instead of `make install`.
    * `make check` runs in build() so CI L1c sees the upstream suite really
      executed (36/36 pass on OHOS).
Artifacts: bin/nq, bin/nqtail, bin/nqterm + man pages (declared via
archives/n/nq/commands.json per R38).
License: CC0-1.0 (public domain).
"""
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class NqConan(ConanFile):
    name = "nq"
    version = "1.0"
    description = "Lightweight Unix job queue with flock(2)-based ordering (nq/nqtail/nqterm)"
    license = "CC0-1.0"
    homepage = "https://github.com/leahneukirchen/nq"
    url = "https://github.com/leahneukirchen/nq"
    topics = ("queue", "job", "flock", "cli", "shell")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        # Plain-Makefile project: build in the same folder the sources live in.
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        if self.settings.os not in ("Linux", "OHOS"):
            self.fail("nq requires a POSIX host (Linux or OHOS)")
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang") if compilers else "clang"
        # R9: -j1; R33: compiler path from Conan conf, not a bare shell variable.
        self.run("make -j1 CC={0}".format(cc))
        # Upstream functional suite: prove -v ./tests (36 TAP assertions).
        self.run("make check")

    def package(self):
        # Direct copy (upstream `make install` needs install(1), which may be
        # missing from PATH in the CI build environment).
        bindir = os.path.join(self.package_folder, "bin")
        mandir = os.path.join(self.package_folder, "share", "man", "man1")
        os.makedirs(bindir, exist_ok=True)
        os.makedirs(mandir, exist_ok=True)
        for exe in ("nq", "nqtail", "nqterm"):
            copy(self, exe, src=self.build_folder, dst=bindir, keep_path=False)
        for man in ("nq.1", "nqtail.1", "nqterm.1"):
            copy(self, man, src=self.build_folder, dst=mandir, keep_path=False)
        for exe in ("nq", "nqtail", "nqterm"):
            os.chmod(os.path.join(bindir, exe), 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
