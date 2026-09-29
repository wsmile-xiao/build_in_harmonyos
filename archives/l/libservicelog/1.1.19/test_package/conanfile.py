#!/usr/bin/env python3
"""test_package for libservicelog 1.1.19.

Consumer E2E, two parts:
  1. probe.c — public v1 API round trip against the installed shared lib
     (open/log/query/print/truncate/close, field-by-field assertions).
  2. run_upstream_tests.sh — upstream's own test driver
     (test_libservicelog.c, shipped inside the package) compiled here as a
     consumer binary, driving the six upstream scenario tests with the
     upstream timestamp-tolerant comparison semantics (POSIX port +
     cmp_tolerant.py, because the upstream bash runner needs GNU
     `diff -y` which the device lacks).

The DB path comes from SERVICELOG_DB (patch 0001 override); the test
writes to a temp dir, so no /var write access is needed.
"""
import os
import tempfile

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import Environment


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # servicelog.h includes sqlite3.h: consumer compile needs the
        # sqlite3 include dir (transitive deps are not exposed via
        # dep.dependencies in the test package context).
        self.requires("sqlite3/3.53.4")

    def _tool(self, key, fallback):
        tools = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        value = tools.get(key) if tools else None
        return value or fallback

    def _dep_dir(self, dep, dirs, fallback):
        d = dirs[0] if dirs else fallback
        return d if os.path.isabs(d) else os.path.join(dep.package_folder, d)

    def build(self):
        dep = self.dependencies["libservicelog"]
        # servicelog.h includes sqlite3.h: the consumer needs the sqlite3
        # include dir as well (declared as an explicit requirement above).
        sqlite_dep = self.dependencies["sqlite3"]
        sqlite_inc = self._dep_dir(sqlite_dep, sqlite_dep.cpp_info.includedirs, "include")
        cc = self._tool("c", "clang")
        inc = os.path.join(self._dep_dir(dep, dep.cpp_info.includedirs, "include"),
                           "servicelog-1")
        libdir = self._dep_dir(dep, dep.cpp_info.libdirs, "lib")
        utests = os.path.join(dep.package_folder, "share", "libservicelog",
                              "upstream-tests")
        rpath = "-Wl,-rpath," + libdir
        self.run("{} {} -I{} -I{} -L{} -lservicelog {} -o test_libservicelog".format(
            cc, os.path.join(utests, "test_libservicelog.c"), inc, sqlite_inc,
            libdir, rpath))
        self.run("{} probe.c -I{} -I{} -L{} -lservicelog {} -o probe".format(
            cc, inc, sqlite_inc, libdir, rpath))

    def test(self):
        if not can_run(self):
            return
        dep = self.dependencies["libservicelog"]
        utests = os.path.join(dep.package_folder, "share", "libservicelog",
                              "upstream-tests")
        tmpdir = tempfile.mkdtemp(prefix="libservicelog-tp-")
        db = os.path.join(tmpdir, "servicelog.db")
        # run(env=list) did not propagate on conan 2.29.1 (SERVICELOG_DB
        # was unset inside the child); apply via Environment.vars().apply().
        env = Environment()
        env.define("SERVICELOG_DB", db)
        env.define("SL_TEST_DB", db)
        env.define("TMPDIR", tmpdir)
        with env.vars(self, scope="run").apply():
            self.run("./probe")
            self.run("sh run_upstream_tests.sh ./test_libservicelog {} cmp_tolerant.py".format(
                os.path.join(utests, "tests-results")))
