#!/usr/bin/env python3
"""Conan test_package — perl-sql-translator (SQL::Translator)
L1-L2 test: verify module files installed AND run functional conversion tests.
"""
import os
import glob

from conan import ConanFile


class PerlSqlTranslatorTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["perl-sql-translator"]
        pkg_folder = dep.package_folder
        self.output.info(f"Package folder: {pkg_folder}")

        # L1: File existence checks
        translator_pm = os.path.join(pkg_folder, "lib", "perl5", "SQL", "Translator.pm")
        assert os.path.exists(translator_pm), f"SQL/Translator.pm not found at {translator_pm}"
        self.output.info("✅ Found SQL/Translator.pm")

        pm_files = glob.glob(os.path.join(pkg_folder, "lib", "perl5", "SQL", "**", "*.pm"), recursive=True)
        self.output.info(f"✅ Found {len(pm_files)} .pm files under SQL/")
        assert len(pm_files) > 50, f"Expected >50 .pm files, got {len(pm_files)}"

        # Check for sqlt script
        sqlt_bin = os.path.join(pkg_folder, "lib", "perl5", "bin", "sqlt")
        assert os.path.exists(sqlt_bin), f"sqlt script not found at {sqlt_bin}"
        self.output.info("✅ Found sqlt script")

        # L2: Functional test — run test script via self.run()
        self.run("sh test_sql_translator.sh", env="conanrun")
