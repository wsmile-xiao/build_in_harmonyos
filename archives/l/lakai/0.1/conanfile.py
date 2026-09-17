#!/usr/bin/env python3
"""Conan recipe for lakai 0.1 — AKAI sampler SCSI transfer tools (pure GNU Makefile).

lakai transfers sampler data (programs, samples) between a PC with a SCSI host
adapter and an AKAI sampler (S1000, S2000, ...).  It ships:

  * liblakai.a  — the link library (header: lakai.h)
  * lakbak      — complete backup of the sampler's memory contents to the PC
  * lakres      — full restore of that data back to the sampler
  * lakclear    — erase all samples/programs currently resident in the sampler

The upstream tree contains a plain GNU Makefile (no configure/autotools/cmake)
and ships NO test suite (no check/test/regress target, no tests/ directory).
This archive therefore adds a self-authored upstream-level suite
(tests/test_lakai.c) plus a `check` target for it (patches/), and runs
`make check` from build() so the tests execute as part of the build.

OHOS adaptations (zero source patches; one Makefile patch that only ADDS a
`check` target):
  * build() passes CC/AR/RANLIB taken from Conan conf (R33) instead of relying
    on the bare shell environment;
  * package() collects the artifacts with Conan copy() instead of calling the
    upstream `install` target, which needs install(1) (unavailable on OHOS);
  * make runs with -j1 (R9, OHOS platform constraint).

Official upstream: https://sourceforge.net/projects/lakai/
License: GPL-2.0-only
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

required_conan_version = ">=2.0"


class LakaiConan(ConanFile):
    name = "lakai"
    version = "0.1"
    description = "AKAI sampler SCSI transfer tools: liblakai static library + lakbak/lakres/lakclear CLIs"
    license = "GPL-2.0-only"
    homepage = "https://sourceforge.net/projects/lakai/"
    url = ""

    # Ships a static library + header + three CLI programs under bin/.
    # The upstream Makefile only produces liblakai.a (no shared library), so the
    # package type is static-library (no `shared` option needed).
    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"

    # The upstream Makefile builds in-source; keep the downloaded sources in
    # place so `make` (run with cwd=source_folder) produces the artifacts there.
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)
        # tests/test_lakai.c is the self-authored upstream-level suite; it must
        # travel with the recipe so the `check` target can compile and run it.
        copy(self, "*",
             src=os.path.join(self.recipe_folder, "tests"),
             dst=os.path.join(self.export_sources_folder, "tests"))

    def requirements(self):
        pass  # zero external deps (only libc + sysroot scsi/sg.h, scsi/scsi.h)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compilers(self):
        # R33: never rely on bare shell $CC/$AR/$RANLIB; read the toolchain
        # paths from Conan conf and pass them explicitly to make below.
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        return {
            "cc": ce.get("c") or "clang",
            "ar": ce.get("ar") or "ar",
            "ranlib": ce.get("ranlib") or "ranlib",
        }

    def build(self):
        # The patch only adds a `check` target (see patches/); the upstream
        # build rules themselves are untouched.
        apply_conandata_patches(self)
        sf = self.source_folder
        tools = self._compilers()

        # Pure Makefile build; -j1 per OHOS platform constraint (R9).  CC comes
        # from Conan conf as an absolute path, not from a shell variable.
        make_flags = "CC={cc} AR={ar} RANLIB={ranlib}".format(**tools)
        self.run("make -j1 {flags}".format(flags=make_flags), cwd=sf)

        # ── Layer-1 tests: `make check` builds and runs tests/test_lakai.c ──
        # The suite links liblakai.a, exercises the character-mapping and handle
        # contracts, and runs the three CLI binaries.  It prints
        # "assertions=N failures=M" and exits non-zero on any failure.
        self.run("make check {flags}".format(flags=make_flags), cwd=sf)

    def package(self):
        sf = self.source_folder
        copy(self, "liblakai.a", sf, os.path.join(self.package_folder, "lib"))
        copy(self, "lakai.h", sf, os.path.join(self.package_folder, "include"))
        for binname in ("lakbak", "lakres", "lakclear"):
            copy(self, binname, sf, os.path.join(self.package_folder, "bin"))
        copy(self, "COPYING", sf, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["lakai"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
