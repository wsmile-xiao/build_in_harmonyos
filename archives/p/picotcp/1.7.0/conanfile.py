#!/usr/bin/env python3
"""Conan recipe — picotcp 1.7.0 (upstream recursive Makefile, static TCP/IP stack).

PicoTCP — small-footprint modular TCP/IP stack. Upstream builds the static
libpicotcp.a via the root Makefile (no configure step). The check-based unit
suites (test/units + test/unit/modunit_*.elf, `make units UNITS=1`) are
compiled and executed in build() against the Conan-provided check/0.15.2.
"""
import glob
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class PicotcpConan(ConanFile):
    name = "picotcp"
    version = "1.7.0"
    description = "PicoTCP — a small footprint, modular TCP/IP stack for embedded systems"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/TASS-Belgium/picotcp"
    url = ""  # CI fills this
    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # check: upstream unit-test framework (<check.h> used by test/units.c
        # and test/unit/modunit_*.c); the suites are executed in build().
        self.requires("check/0.15.2")

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _make(self, prefix, extra=""):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang") if compilers else "clang"
        return (
            f"make CC={cc} AR=llvm-ar DEBUG=0 PROFILE=0 PERF=0 "
            f"ADDRESS_SANITIZER=0 GCOV=0 STRIP=0 PREFIX={prefix} -j2 {extra}"
        )

    def build(self):
        apply_conandata_patches(self)
        sf = self.source_folder
        dist = os.path.join(sf, "conan-dist")
        dist_units = os.path.join(sf, "conan-dist-units")
        check = self.dependencies["check"]
        check_inc = os.path.join(check.package_folder, check.cpp_info.includedirs[0])
        check_lib = os.path.join(check.package_folder, check.cpp_info.libdirs[0])

        # Pass 1: upstream unit suites. UNITS=1 compiles the stack with
        # -DUNIT_TEST/-DFAULTY. 6LOWPAN/IEEE802154 are disabled by upstream
        # default, but the `units` target links their modunit_*.elf against
        # libpicotcp.a, so the modules must be compiled in for the tests.
        # The Makefile patch routes the check framework paths through
        # CONAN_UNIT_* (upstream UNIT_CFLAGS/UNIT_LDFLAGS keep inheriting
        # CFLAGS, which carries the per-module -D flags) and drop -lsubunit
        # (the check/0.15.2 package is built without subunit).
        self.run(
            self._make(
                dist_units,
                extra=(
                    "UNITS=1 6LOWPAN=1 IEEE802154=1 "
                    f"CONAN_UNIT_LDFLAGS='-L{check_lib}' "
                    f"CONAN_UNIT_CFLAGS='-I{check_inc}' units"
                ),
            ),
            cwd=sf,
        )
        # check(3) returns the number of failed checks: any non-zero exit
        # fails the build with the suite output attached. The check framework
        # builds its IPC temp file in `TEMP` -> P_tmpdir -> TMPDIR -> "."
        # priority; the OHOS host /tmp is read-only, so TEMP is redirected to
        # a writable directory (TMPDIR alone is shadowed by P_tmpdir).
        tmpdir = os.path.join(self.build_folder, "check-tmp")
        os.makedirs(tmpdir, exist_ok=True)
        suites = sorted(glob.glob(os.path.join(dist_units, "test", "*.elf")))
        suites.append(os.path.join(dist_units, "test", "units"))
        test_dir = os.path.dirname(suites[0])
        for suite in suites:
            self.run(
                f'TEMP="{tmpdir}" TMPDIR="{tmpdir}" LD_LIBRARY_PATH="{check_lib}" '
                f'"./{os.path.basename(suite)}"',
                cwd=test_dir,
            )

        # Pass 2: clean rebuild with the upstream default module set for
        # packaging (in-tree stack/*.o and modules/*.o are stale from pass 1;
        # upstream `make clean` only removes the PREFIX tree).
        self.run("make clean " + f"PREFIX={dist_units}", cwd=sf)
        self.run("rm -f stack/*.o modules/*.o", cwd=sf)
        self.run(self._make(dist), cwd=sf)

    def package(self):
        dist = os.path.join(self.source_folder, "conan-dist")
        # The build flattens every public header (include/, stack/, modules/)
        # into $(PREFIX)/include, with the generated pico_defines.h and the
        # arch/ platform headers; that tree is the complete API surface.
        copy(self, "*", src=os.path.join(dist, "include"),
             dst=os.path.join(self.package_folder, "include"), keep_path=True)
        copy(self, "lib/libpicotcp.a", src=dist,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["picotcp"]
