#!/usr/bin/env python3
"""Conan test_package — perl-sql-statement 1.414-r1.

Runs test_sql_statement.sh which verifies .pm file packaging, performs
perl -c syntax checks, and attempts a minimal API call (module load).
"""
from conan import ConanFile


class PerlsqlstatementTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        self.run("sh test_sql_statement.sh", env="conanrun")
