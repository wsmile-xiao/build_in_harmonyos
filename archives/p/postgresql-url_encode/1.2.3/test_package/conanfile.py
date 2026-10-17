#!/usr/bin/env python3
"""Conan test_package for postgresql-url_encode 1.2.3 — live-server test."""
import os

from conan import ConanFile


class TestPackage(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # PostgreSQL server binaries (initdb/pg_ctl/psql/pg_config) for
        # the live functional test.
        self.requires("postgresql/18.3")

    def test(self):
        pg = self.dependencies["postgresql"]
        pkg = self.dependencies["postgresql-url_encode"]
        pg_bindir = pg.cpp_info.bindirs[0]
        pkg_libdir = pkg.cpp_info.libdirs[0]
        pkg_sharedir = pkg.cpp_info.resdirs[0]
        script = os.path.join(self.source_folder, "run_pg_test.sh")
        self.run(f'bash "{script}" "{pg_bindir}" "{pkg_libdir}" "{pkg_sharedir}"',
                 env="conanrun")
