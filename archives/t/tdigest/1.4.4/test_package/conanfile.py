#!/usr/bin/env python3
"""Conan test_package for tdigest 1.4.4 — live-server upstream regression test.

A PostgreSQL extension only proves itself inside a running server: the module
is dlopen-ed by the postgres process at CREATE EXTENSION time, and every
PostgreSQL symbol is resolved against that process. The test therefore boots a
throwaway PostgreSQL 18.3 cluster (relocated out of the conan cache), installs
the *packaged* tdigest.so / tdigest.control / tdigest--*.sql into it and
replays the upstream regression suite (10 test groups) with pg_regress, plus
OHOS-specific assertions (module ABI, /tmp read-only workaround, live
aggregate query). See MANIFEST.yml and run_pg_test.sh.
"""
import os

from conan import ConanFile


class TdigestTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # PostgreSQL server binaries (initdb/pg_ctl/psql/pg_regress/pg_config)
        # and the server headers required by the extension build.
        self.requires("postgresql/18.3")

    @staticmethod
    def _abs(base, path):
        return path if os.path.isabs(path) else os.path.join(base, path)

    def test(self):
        pg = self.dependencies["postgresql"]
        pkg = self.dependencies["tdigest"]
        pg_bindir = self._abs(pg.package_folder, pg.cpp_info.bindirs[0])
        # Deliberately taken from the tested package (never from a system
        # PostgreSQL), so CI's L1e negative test — sabotage the package
        # artifacts and re-run — genuinely fails.
        pkg_libdir = self._abs(pkg.package_folder, pkg.cpp_info.libdirs[0])
        pkg_sharedir = self._abs(pkg.package_folder, pkg.cpp_info.resdirs[0])
        # The whole test_package folder is copied into the conan cache, so the
        # staged upstream test tree sits next to this conanfile.
        here = self.recipe_folder
        tests_dir = here if os.path.isfile(os.path.join(here, "run_pg_test.sh")) \
            else os.path.join(here, "test_package")
        script = os.path.join(tests_dir, "run_pg_test.sh")
        self.run(
            f'bash "{script}" "{pg_bindir}" "{pkg_libdir}" "{pkg_sharedir}" "{tests_dir}"',
            env="conanrun")
