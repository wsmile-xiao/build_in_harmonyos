import os
import shlex
import sys

from conan import ConanFile
from conan.errors import ConanException


class PgCrashTestConan(ConanFile):
    """Consumer test for the pg_crash package.

    The heavy lifting lives in ``pgcrash_test.py`` (artifact assertions
    and a real PostgreSQL server driving the shared_preload_libraries
    load path plus GUC/worker assertions).  This file is the Conan
    driver entry point.
    """

    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        # pg_config + server + initdb/pg_ctl/psql used to boot a throw-away
        # cluster that preloads the packaged module.
        self.tool_requires("postgresql/16.10")

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
        dep = self.dependencies["pg-crash"]
        pkg = dep.package_folder
        if not pkg:
            raise ConanException("pg-crash package folder not populated")

        harness = os.path.join(self.source_folder, "pgcrash_test.py")
        if not os.path.isfile(harness):
            raise ConanException(f"test driver not found: {harness}")

        cmd = [sys.executable, harness, "--package", pkg]
        bindir = self._postgres_bindir()
        if bindir:
            cmd += ["--pg-bindir", bindir]

        self.output.info("pg_crash consumer harness: " + " ".join(cmd))
        self.run(" ".join(shlex.quote(part) for part in cmd),
                 env="conanbuild")
