#!/usr/bin/env python3
"""Conan recipe for smemstat 0.02.13 — kernel memory usage reporter (direct make).

Upstream: https://github.com/ColinIanKing/smemstat (tag V0.02.13, GPL-2.0)
Binary: bin/smemstat (ncurses memory reporter, links -lncursesw -lm).

OHOS adaptation:
- Plain Makefile project (no configure, no autotools). Build via the
  upstream Makefile with command-line variable overrides: CC comes from
  the profile `tools.build:compiler_executables` (R33), and CFLAGS is
  fully re-supplied including `-DVERSION` because command-line make
  variables silence the Makefile's `CFLAGS +=` default (which carries
  the VERSION define upstream).
- ncurses/6.6 from the ohpcd registry (static wide build providing
  libncursesw) satisfies the hard `-lncursesw`; static linking also
  avoids shadowing any system ncurses (R26 class).
- No `make install` on HMDFS (install-sh/chmod class issues,
  dhcpoptinj/0.5.3 precedent): package() stages with pure-Python copy.
- Upstream ships no test suite (no tests/ dir, no check target in the
  Makefile): build() does not fake a check run; the audit lives in
  test_package/MANIFEST.yml and the consumer test runs the packaged
  binary (R34).
"""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class SmemstatConan(ConanFile):
    name = "smemstat"
    version = "0.02.13"
    description = "Kernel memory usage reporter with ncurses display"
    license = "GPL-2.0-only"
    homepage = "https://github.com/ColinIanKing/smemstat"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("memory", "procfs", "monitoring")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        self.folders.source = "."
        self.folders.build = "."
        self.folders.generators = "."

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "smemstat is built for Linux/OHOS only"
            )

    def requirements(self):
        self.requires("ncurses/6.6")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        cc = (self.conf.get("tools.build:compiler_executables") or {}).get(
            "c", "clang"
        )
        dep = self.dependencies.get("ncurses")
        inc0 = dep.cpp_info.includedirs[0]
        lib0 = dep.cpp_info.libdirs[0]
        dep_inc = inc0 if os.path.isabs(inc0) else os.path.join(dep.package_folder, inc0)
        dep_lib = lib0 if os.path.isabs(lib0) else os.path.join(dep.package_folder, lib0)
        jobs = self.conf.get("tools.build:jobs", default=1)
        # Command-line CFLAGS fully replaces the Makefile default
        # (`CFLAGS +=` is a no-op for command-line variables), so the
        # upstream VERSION define is re-supplied in the upstream quoting
        # form `-DVERSION='"X.Y.Z"'` (dhcpoptinj/0.5.3 precedent).
        cflags = f"-O2 -fPIC -DVERSION='\"{self.version}\"' -I{dep_inc}"
        ldflags = f"-L{dep_lib}"
        self.run(
            f'make -C "{self.source_folder}" -j{jobs} '
            f'CC="{cc}" '
            f"CFLAGS={shlex.quote(cflags)} "
            f"LDFLAGS={shlex.quote(ldflags)} "
            f"smemstat",
        )

    def package(self):
        copy(
            self,
            "smemstat",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "bin"),
        )
        copy(
            self,
            "smemstat.8",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "man", "man8"),
        )
        copy(
            self,
            "smemstat",
            src=os.path.join(self.source_folder, "bash-completion"),
            dst=os.path.join(
                self.package_folder, "share", "bash-completion", "completions"
            ),
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
