import os
import shlex
import sys

from conan import ConanFile
from conan.errors import ConanException


class PgvectorTestConan(ConanFile):
    """Consumer test for the pgvector package.

    The heavy lifting lives in ``pgvector_test.py`` (artifact assertions,
    a real PostgreSQL server driving SQL assertions, and the upstream
    pg_regress suite).  This file is the Conan driver entry point.
    """

    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        # pg_config + PGXS-less runtime: postgres/initdb/pg_ctl/createdb/psql
        # used to boot a throw-away cluster for the functional checks.
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
        dep = self.dependencies["pgvector"]
        pkg = dep.package_folder
        if not pkg:
            raise ConanException("pgvector package folder not populated")

        harness = os.path.join(self.source_folder, "pgvector_test.py")
        if not os.path.isfile(harness):
            raise ConanException(f"test driver not found: {harness}")

        cmd = [sys.executable, harness, "--package", pkg]
        bindir = self._postgres_bindir()
        if bindir:
            cmd += ["--pg-bindir", bindir]

        self.output.info("pgvector consumer harness: " + " ".join(cmd))
        self.run(" ".join(shlex.quote(part) for part in cmd),
                 env="conanbuild")
