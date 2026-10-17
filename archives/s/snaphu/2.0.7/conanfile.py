#!/usr/bin/env python3
"""Conan recipe — snaphu 2.0.7 (bare Makefile CLI application).

snaphu is the SNAPHU statistical-cost network-flow phase-unwrapping program
from Stanford Radar Interferometry. The tarball ships one Makefile under src/:
there is no configure script, no usable install target (upstream only copies
into /usr/local/bin + /usr/local/man) and no test suite at all.

OHOS notes:
  - src/Makefile hardcodes `CC = cc`, `CFLAGS = -arch x86_64 -O3 -Wall`
    (`-arch x86_64` is macOS-only and clang would read it as a target
    architecture) and `BINDIR = ../bin`; build() overrides all three on the
    make command line and takes the compiler from the Conan profile (R33).
  - package() installs bin/snaphu by hand and chmods it 0755 (upstream's own
    install target is unusable off the maintainer's machine).
  - Upstream ships no tests (N_static = 0: no check/test target and no test
    sources), so the deliverable is verified by the consumer test in
    test_package/, which drives the real binary end-to-end (R34/R51).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get, mkdir)
from conan.tools.layout import basic_layout


class SnaphuConan(ConanFile):
    name = "snaphu"
    version = "2.0.7"
    description = ("SNAPHU: statistical-cost, network-flow algorithm for "
                   "two-dimensional phase unwrapping (InSAR interferometry)")
    license = "LicenseRef-Stanford"
    homepage = "https://web.stanford.edu/group/radar/softwareandlinks/sw/snaphu/"
    url = "https://web.stanford.edu/group/radar/softwareandlinks/sw/snaphu/"
    topics = ("insar", "phase-unwrapping", "interferometry", "remote-sensing")
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # snaphu links against libm only — no third-party dependencies.
        pass

    def validate(self):
        # R32: OHOS must be matched alongside Linux, never `== "Linux"`.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"snaphu supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler_c(self):
        # R33: take the compiler from the Conan profile, never from ${CC}.
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return executables.get("c") or "clang"

    def generate(self):
        # Record the resolved compiler in the build env for traceability.
        env = Environment()
        env.define("CC", self._compiler_c())
        env.vars(self).save_script("conanbuild_cc")

    def build(self):
        apply_conandata_patches(self)

        cc = self._compiler_c()
        # Sources live one level below the tarball root; the binary goes to
        # $(BINDIR), which we point at the build tree.
        srcdir = os.path.join(self.source_folder, "src")
        bindir = os.path.join(self.build_folder, "bin")
        mkdir(self, bindir)
        cflags = "-O3 -Wall"
        self.run(
            f'make CC="{cc}" CFLAGS="{cflags}" BINDIR="{bindir}" LIBS="-lm" -j1',
            cwd=srcdir,
        )

    def package(self):
        copy(self, "snaphu", src=os.path.join(self.build_folder, "bin"),
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "snaphu.1", src=os.path.join(self.source_folder, "man", "man1"),
             dst=os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "README", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        os.chmod(os.path.join(self.package_folder, "bin", "snaphu"), 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
