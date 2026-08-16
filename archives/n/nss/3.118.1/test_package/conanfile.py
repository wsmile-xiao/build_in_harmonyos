#!/usr/bin/env python3
"""Conan test_package — NSS 3.118.1

L1 test: compile test.c against the packaged NSS headers and link, then run
the binary. The test really initializes NSS (NSS_NoDB_Init loads softoken /
freebl) and performs a SHA-256 hash against the NIST "abc" vector, plus
NSS_GetVersion and SEC_OID constant assertions.

NSS coreconf produces both libnss.a (aggregator stub) and libnss3.so
(fully aggregated shared lib exporting all internal symbols). The test links
the shared libraries, which resolve every symbol, avoiding the long static
dependency chain (pk11wrap, certdb, certhi, cryptohi, pkix*...).
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building


class NssTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Collect include dirs from all deps (nss + transitive nspr)
        incs = []
        libdirs = []
        for _, dep in self.dependencies.items():
            incs += ["-I" + p for p in dep.cpp_info.includedirs]
            libdirs += ["-L" + p for p in dep.cpp_info.libdirs]
        cc = os.environ.get("CC", "clang")
        # Shared libs: fully aggregated, resolve all NSS internal symbols.
        # test.c is copied next to this recipe into the test build dir.
        rpaths = ":".join(d.cpp_info.libdirs[0]
                          for _, d in self.dependencies.items())
        self.run(f"{cc} test.c -o test_nss "
                + " ".join(incs + libdirs)
                + " -lnss3 -lssl3 -lsmime3 -lnssutil3 -lsoftokn3 -lfreebl3"
                + " -lnssdbm3 -lsqlite3 -lnssckbi"
                + " -lnspr4 -lplc4 -lplds4"
                + " -ldl -lpthread -lz"
                + f" -Wl,-rpath,{rpaths}")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile+link only")
            return
        # OHOS HMDFS restricts the default temp dir (E165/E186 class issue):
        # a writable TMPDIR is required; use the Conan build folder instead of
        # a hard-coded developer machine path (R33).
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        # softoken is dlopen()'d at runtime by libnss3 -> needs LD_LIBRARY_PATH.
        libs = ":".join(d.cpp_info.libdirs[0]
                        for _, d in self.dependencies.items())
        self.run(f"LD_LIBRARY_PATH={libs}:$LD_LIBRARY_PATH "
                 f"TMPDIR={tmpdir} ./test_nss", env="conanrun")
