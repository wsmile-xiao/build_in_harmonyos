#!/usr/bin/env python3
"""Conan test_package — perl-sql-abstract-pg 1.0

Consumer-side tests for SQL::Abstract::Pg module:
- Module load and version verification
- Basic INSERT/SELECT/UPDATE/DELETE
- ON CONFLICT (DO NOTHING, DO UPDATE, multi-column, literal SQL)
- LIMIT/OFFSET
- GROUP BY / HAVING
- ORDER BY (legacy and hashref)
- FOR UPDATE / FOR UPDATE SKIP LOCKED
- AS (field aliases, literal SQL, bind values)
- JSON operator
- JOIN (INNER, LEFT, RIGHT, multi-join, multi-condition)
- Error handling for unsupported values
- Combined query with all clauses
"""
import os
import glob

from conan import ConanFile


class PerlSqlAbstractPgTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find SQL/Abstract/Pg.pm in the package folder
        pkg = self.dependencies["perl-sql-abstract-pg"]
        pkg_folder = pkg.package_folder
        pm_files = glob.glob(os.path.join(pkg_folder, "**", "Pg.pm"), recursive=True)
        if not pm_files:
            raise Exception("SQL/Abstract/Pg.pm not found in package")
        # SQL::Abstract::Pg is a 3-level module path (SQL/Abstract/Pg.pm),
        # so we need 3x dirname to get the PERL5LIB root
        lib_dir = os.path.dirname(os.path.dirname(os.path.dirname(pm_files[0])))

        # Also include DEFAULT_PREFIX/lib/perl5 for SQL::Abstract dependency
        # (not declared as conan requirement — pre-installed in system)
        default_prefix = os.environ.get("DEFAULT_PREFIX", "")
        dep_lib = os.path.join(default_prefix, "lib", "perl5") if default_prefix else ""

        test_script = os.path.join(self.source_folder, "run_test.sh")
        self.run(f"sh {test_script} {lib_dir} {dep_lib}")
