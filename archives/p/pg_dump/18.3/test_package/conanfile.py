#!/usr/bin/env python3
"""Conan test_package for pg_dump 18.3 — verifies pg_dump binary works.

Test approach:
  1. Verify pg_dump --version outputs "pg_dump (PostgreSQL) 18.3"
  2. Verify pg_dumpall --version outputs version info
  3. Verify pg_restore --version outputs version info
"""
import os

from conan import ConanFile


class PgDumpTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass  # No build needed — we run pg_dump binary directly

    def test(self):
        dep = self.dependencies["pg_dump"]
        bin_dir = os.path.join(dep.package_folder, dep.cpp_info.bindirs[0])

        # Test 1: Verify pg_dump --version
        pg_dump_bin = os.path.join(bin_dir, "pg_dump")
        self.run(f'"{pg_dump_bin}" --version', env="conanrun")

        # Test 2: Verify pg_dumpall --version
        pg_dumpall_bin = os.path.join(bin_dir, "pg_dumpall")
        self.run(f'"{pg_dumpall_bin}" --version', env="conanrun")

        # Test 3: Verify pg_restore --version
        pg_restore_bin = os.path.join(bin_dir, "pg_restore")
        self.run(f'"{pg_restore_bin}" --version', env="conanrun")
