#!/usr/bin/env python3
"""Conan test_package for libmaxminddb 1.13.3 — Conan L1 official test.

Builds test_package.c with CMake and links it against the libmaxminddb
package (find_package(libmaxminddb) -> libmaxminddb::libmaxminddb,
links -lmaxminddb).

The test performs a REAL MMDB read against the bundled upstream test
database (data/MaxMind-DB-test-ipv4-28.mmdb, taken from the upstream
t/maxmind-db/test-data tree), mirroring t/basic_lookup_t.c:
  MMDB_open(..., MMDB_MODE_MMAP, ...)
    -> MMDB_lookup_string(&mmdb, "1.1.1.1", ...)  (found_entry == true)
    -> MMDB_get_value(&result.entry, &v, "ip", NULL) == "1.1.1.1"
    -> MMDB_close(&mmdb)
test() actually runs the compiled binary via self.run (R34/PF3 — no
print-only stub).
"""
import base64
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibMaxMindDBTestConan(ConanFile):
    test_type = "explicit"
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Decode the base64-stored upstream test database (stored as text so
        # GitCode's PR diff — which carries no binary patch data — applies
        # cleanly in CI checkout-pr; same convention as aircrack/blur).
        src = os.path.join(self.source_folder, "data", "MaxMind-DB-test-ipv4-28.mmdb.b64")
        dst = os.path.join(self.build_folder, "MaxMind-DB-test-ipv4-28.mmdb")
        with open(src, encoding="ascii") as f, open(dst, "wb") as out:
            out.write(base64.b64decode(f.read()))

        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries directly.
        # Wrap with bash (same proven pattern as zlib/1.3.1 test_package).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_libmaxminddb'", env="conanrun")
