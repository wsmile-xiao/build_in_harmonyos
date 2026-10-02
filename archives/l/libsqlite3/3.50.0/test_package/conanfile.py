#!/usr/bin/env python3
"""Conan consumer test for libsqlite3 3.50.0.

Two end-to-end consumer exercises run against the produced package:

* test_sqlite3 -- in-process C API consumer: persistence CRUD lifecycle,
  query-engine paths (JOIN/aggregate/FTS5/RTREE) and metadata contract.
* sqlite3 CLI -- shipped-tool consumer flow: create a database through the
  packaged CLI, run a verification query guarded by a RAISE(ABORT) trigger,
  export .dump, re-import into a second database and verify there too.
"""

import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class Sqlite3TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _prefix(self):
        qemu = os.environ.get("OHOS_QEMU")
        runroot = os.environ.get("OHOS_RUNROOT", "")
        if qemu:
            args = [qemu]
            if runroot:
                args += ["-L", runroot]
            return " ".join(args)
        return ""

    def _cli_path(self):
        suffix = ".exe" if str(self.settings.os) == "Windows" else ""
        return os.path.join(
            self.dependencies["libsqlite3"].package_folder, "bin", "sqlite3" + suffix)

    def _run_cli(self, db, sql):
        prefix = self._prefix()
        quoted = sql.replace('"', '\\"')
        self.run('{} "{}" "{}" "{}"'.format(prefix, self._cli_path(), db, quoted), env="conanrun")

    def _run_cli_script(self, db, script):
        prefix = self._prefix()
        self.run('{} "{}" "{}" < "{}"'.format(prefix, self._cli_path(), db, script), env="conanrun")

    def _cli_e2e(self):
        """Consumer end-to-end flow through the packaged sqlite3 CLI."""
        cli = self._cli_path()
        if not os.path.isfile(cli):
            raise Exception("packaged sqlite3 CLI not found: {}".format(cli))
        work = self.build_folder
        db1 = os.path.join(work, "cli_e2e.db")
        db2 = os.path.join(work, "cli_e2e_reimport.db")
        dump = os.path.join(work, "cli_e2e.sql")
        for path in (db1, db2, dump):
            if os.path.exists(path):
                os.remove(path)

        # 1) create schema + data through the CLI
        self._run_cli(db1,
            "CREATE TABLE orders(id INTEGER PRIMARY KEY, sku TEXT, qty INT);"
            "INSERT INTO orders(sku, qty) VALUES('a', 1), ('b', 2), ('c', 3);")

        # 2) export with .dump through the CLI
        script = os.path.join(work, "cli_e2e_dump.cmd")
        with open(script, "w", encoding="utf-8") as handle:
            handle.write('.output "{}"\n.dump\n.exit\n'.format(dump))
        self._run_cli_script(db1, script)
        if not os.path.isfile(dump):
            raise Exception("CLI .dump produced no file")
        with open(dump, encoding="utf-8") as handle:
            dump_text = handle.read()
        if ("CREATE TABLE orders" not in dump_text
                or "INSERT INTO orders" not in dump_text
                or "'a'" not in dump_text or "'b'" not in dump_text or "'c'" not in dump_text):
            raise Exception("CLI .dump content incomplete: {}".format(dump_text[:200]))

        # 3) re-import the dump into a fresh database
        self._run_cli_script(db2, dump)

        # 4) verification query on both databases: the CLI must fail loudly on
        #    any mismatch (RAISE(ABORT) inside a guard trigger)
        verify = (
            "DROP TABLE IF EXISTS chk;"
            "CREATE TABLE chk(x INT);"
            "CREATE TRIGGER guard BEFORE INSERT ON chk BEGIN "
            "SELECT CASE WHEN (SELECT COUNT(*) FROM orders) <> 3 "
            "OR (SELECT SUM(qty) FROM orders) <> 6 "
            "THEN RAISE(ABORT, 'CLI_E2E_MISMATCH') END; END;"
            "INSERT INTO chk VALUES(1);")
        self._run_cli(db1, verify)
        self._run_cli(db2, verify)
        self.output.info("cli e2e: create -> .dump -> re-import -> verify (both DBs) OK")

    def test(self):
        qemu = os.environ.get("OHOS_QEMU")
        if qemu:
            self.run("{} ./test_sqlite3".format(self._prefix()), env="conanrun")
            self._cli_e2e()
            return
        if cross_building(self):
            self.output.info("cross-building: compile and link completed; target execution is deferred")
            return
        if str(self.settings.os) == "Windows":
            self.run("test_sqlite3.exe", env="conanrun")
            self._cli_e2e()
            return
        bash = os.environ.get("CONFIG_SHELL", "bash")
        self.run("{} -c './test_sqlite3'".format(bash), env="conanrun")
        self._cli_e2e()
