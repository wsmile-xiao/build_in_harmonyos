import os
import shlex
import sys

from conan import ConanFile
from conan.errors import ConanException


class PgcopydbTestConan(ConanFile):
    """Consumer test for the pgcopydb package.

    The heavy lifting lives in ``pgcopydb_test.py``: artifact assertions plus a
    full copy of a real database between two throw-away PostgreSQL 18.3
    instances.  This file is only the Conan driver entry point.
    """

    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["pgcopydb"]
        package = dep.package_folder
        if not package:
            raise ConanException("pgcopydb package folder not populated")

        binary = os.path.join(package, "bin", "pgcopydb")
        if not os.path.isfile(binary):
            raise ConanException(f"pgcopydb binary not found: {binary}")

        # The server binaries (initdb/postgres/psql/pg_dump/pg_restore) come
        # from the postgresql package that pgcopydb itself depends on.
        pg = self.dependencies["postgresql"].package_folder
        if not pg or not os.path.isfile(os.path.join(pg, "bin", "initdb")):
            raise ConanException("postgresql dependency does not provide initdb")

        harness = os.path.join(self.source_folder, "pgcopydb_test.py")
        if not os.path.isfile(harness):
            raise ConanException(f"test driver not found: {harness}")

        # /tmp is read-only on HarmonyOS: use a writable scratch directory.
        workdir = os.environ.get("TMPDIR") or ""
        if not workdir or not os.path.isdir(workdir) or not os.access(workdir, os.W_OK):
            workdir = os.path.join(os.path.expanduser("~"), "tmp")
        os.makedirs(workdir, exist_ok=True)

        cmd = [sys.executable, harness, pg, binary, workdir]
        self.output.info("pgcopydb consumer harness: " + " ".join(cmd))
        self.run(" ".join(shlex.quote(part) for part in cmd), env="conanbuild")
