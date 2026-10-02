#!/usr/bin/env python3
"""Consumer test for the pgtap/1.3.4 package (PGXS, PostgreSQL TAP extension).

Conan driver entry point: starts a real PostgreSQL 18.3 instance and runs
``pgtap_test.py`` (artifact assertions + live SQL/TAP consumer assertions +
the upstream pg_regress groups).
"""
import os
import shlex
import sys

from conan import ConanFile
from conan.errors import ConanException


class PgtapTestConan(ConanFile):
    """Consumer test for the pgTAP package.

    The heavy lifting lives in ``pgtap_test.py`` (artifact assertions, a real
    PostgreSQL server driving SQL/TAP assertions, and the upstream pg_regress
    suite).  This file is the Conan driver entry point.
    """

    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        # Full server used to boot a throw-away cluster for the functional
        # checks: postgres / initdb / pg_ctl / createdb / psql.
        self.tool_requires("postgresql/18.3")

    def _postgres_bindir(self):
        try:
            dep = self.dependencies.build["postgresql"].cpp_info
            for bindir in dep.bindirs:
                if os.path.isfile(os.path.join(bindir, "pg_config")):
                    return bindir
        except Exception:                                     # noqa: BLE001
            pass
        return ""

    def test(self):
        dep = self.dependencies["pgtap"]
        pkg = dep.package_folder
        if not pkg:
            raise ConanException("pgtap package folder not populated")

        harness = os.path.join(self.source_folder, "pgtap_test.py")
        if not os.path.isfile(harness):
            raise ConanException(f"test driver not found: {harness}")

        cmd = [sys.executable, harness, "--package", pkg]
        bindir = self._postgres_bindir()
        if bindir:
            cmd += ["--pg-bindir", bindir]

        self.output.info("pgtap consumer harness: " + " ".join(cmd))
        self.run(" ".join(shlex.quote(part) for part in cmd),
                 env="conanbuild")
