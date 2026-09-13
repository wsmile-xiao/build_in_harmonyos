#!/usr/bin/env python3
"""Conan recipe for detenc 2.0.0 — heuristic character-encoding detector CLI.

Build system: plain recursive Makefile (no configure/cmake).

Adaptation notes for HarmonyOS:
- src/Makefile hardcodes `CC = gcc`. A Makefile assignment beats the
  environment, so CC is overridden as a command-line make variable taken
  from Conan conf (R33: never bare ${CC} in self.run()).
- Upstream CFLAGS is only -Wall; -O2 is added for a Release-grade binary.
  No -fPIC needed: the product is a single executable, not a library.
- Upstream test suite is Ruby minitest driven by the root Makefile `check`
  target (`cd test && rake test`). It is run inside build() so CI can verify
  upstream tests actually executed (L1c).
- The suite creates its inputs via Ruby Tempfile, which honours TMPDIR;
  OHOS /tmp is read-only (E002), so TMPDIR is pointed at the Conan build
  folder for the test run.
- Test files use the pre-minitest-5 spelling `MiniTest::Test`; that alias
  was removed in minitest 5.x (device ships 5.25.4) and is fixed by patch
  0001 with the same approach as Alpine's APKBUILD.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class DetencConan(ConanFile):
    name = "detenc"
    version = "2.0.0"
    description = "Lightweight heuristic character-encoding detector for Western European text"
    license = "MIT"
    homepage = "https://github.com/reevoo/detenc"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    # No options: single self-contained executable, zero dependencies.

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: resolve the compiler from Conan conf, never from shell env vars.
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        # R9: -j1. Command-line variables override src/Makefile's `CC = gcc`
        # (environment variables would NOT: a Makefile assignment wins).
        # `make check` builds bin/detenc then runs `cd test && rake test`
        # (upstream Ruby minitest suite). TMPDIR must point to a writable
        # location on OHOS (E002: /tmp is read-only).
        tmpdir = self.build_folder.replace("\\", "/")
        self.run(
            f'TMPDIR="{tmpdir}" make check -j1 CC="{cc}" CFLAGS="-Wall -O2"',
            cwd=self.source_folder,
        )

    def package(self):
        copy(
            self,
            "detenc",
            src=os.path.join(self.source_folder, "bin"),
            dst=os.path.join(self.package_folder, "bin"),
        )

    def package_info(self):
        # Command-line tool, not a library.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
