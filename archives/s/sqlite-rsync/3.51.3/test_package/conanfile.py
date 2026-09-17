#!/usr/bin/env python3
"""test_package for sqlite-rsync — runs test_sqlite_rsync.sh which exercises the binary.

The script performs a fail-able functional round-trip: it creates a source
database with the Python sqlite3 module (available on every CI worker per the
ci/conan/setup.sh contract), syncs it with sqlite3_rsync, and asserts the
replica content row-by-row. It also regression-checks the argv hardening
backport (unknown dash-options must be rejected with "unknown option").
"""
import os

from conan import ConanFile


class SqliteRsyncTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # conanrun env puts the package's bin/ on PATH, so sqlite3_rsync resolves.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'"{bash}" test_sqlite_rsync.sh', env="conanrun")
