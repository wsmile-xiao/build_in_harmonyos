#!/usr/bin/env python3
"""Conan recipe — soci 4.1.4 (C++ database access layer).

SOCI ("Simple Oracle Call Interface", long since grown into a general database
access layer) presents one C++ API over several database backends: a session,
statements with `into`/`use` bindings, rowset iteration and stored procedure
calls, all with compile-time type safety.

Build system : CMake.
Backends     : backends are selected with ``SOCI_<NAME>`` cache variables that
               accept ON/OFF/AUTO.  This package enables only the two backends
               that need no external server:

                 * ``SQLite3`` — needs sqlite3 (a Conan requirement here)
                 * ``Empty``   — a do-nothing backend used by SOCI's own tests

               DB2, Firebird, MySQL, ODBC, Oracle and PostgreSQL are explicitly
               turned OFF: they either need a proprietary client library or a
               live database server, neither of which belongs in this package.
Package form : a library — ``lib/libsoci_core.a`` plus one library per enabled
               backend, and the headers under ``include/soci/``.  No executables
               are installed, so no commands.json is required.

Dependencies : ``sqlite3`` (for the SQLite3 backend) and ``fmt``.  Upstream
               normally vendors fmt as a git submodule under ``3rdparty/fmt``,
               which a GitHub archive tarball does not contain — ``fmt`` is a
               real Conan dependency here and ``SOCI_FMT_BUILTIN=OFF`` makes a
               missing fmt fail loudly instead of silently falling back.

Upstream tests: SOCI's own Catch2-based suite (Catch is vendored in tests/).
``build()`` builds and runs it.  See test_package/MANIFEST.yml for the counts —
note in particular that the number of test cases that actually run is what
Catch2 reports, not the number of ``TEST_CASE`` lines in the sources.
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import get

# Backends that need a proprietary client library or a live server.
DISABLED_BACKENDS = ("DB2", "FIREBIRD", "MYSQL", "ODBC", "ORACLE", "POSTGRESQL")


class SociConan(ConanFile):
    name = "soci"
    version = "4.1.4"
    description = ("SOCI — C++ database access layer (core + SQLite3 and Empty "
                   "backends)")
    license = "BSL-1.0"
    homepage = "https://github.com/SOCI/soci"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "soci is prepared for Linux/OHOS targets only")

    def requirements(self):
        # the SQLite3 backend
        self.requires("sqlite3/3.53.4")
        # upstream vendors fmt as a submodule, absent from the archive tarball
        self.requires("fmt/11.1.3")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)

        # SOCI looks for SQLite3 with `find_package(SQLite3)` and expects the
        # target that CMake's own FindSQLite3 module defines -- `SQLite::SQLite3`
        # on CMake < 4.3, `SQLite3::SQLite3` on 4.3+.  Conan's sqlite3 package
        # declares `sqlite3-config.cmake` / `sqlite3::sqlite3` instead, and
        # because find_package also matches the lower-cased `<name>-config.cmake`
        # form, config mode wins and SOCI's check for its expected target fails:
        #
        #   Expected successful find_package call with 'SQLite3' to define
        #   target 'SQLite::SQLite3'
        #
        # CMakeDeps.set_property() is the supported way to override these names
        # from the consumer side.  The alias covers the CMake >= 4.3 spelling so
        # the package does not depend on which CMake the consumer runs.
        deps.set_property("sqlite3", "cmake_file_name", "SQLite3")
        deps.set_property("sqlite3", "cmake_target_name", "SQLite::SQLite3")
        deps.set_property("sqlite3", "cmake_target_aliases", ["SQLite3::SQLite3"])
        deps.generate()

        tc = CMakeToolchain(self)
        tc.variables["SOCI_SHARED"] = bool(self.options.shared)
        tc.variables["SOCI_TESTS"] = True
        tc.variables["SOCI_INSTALL"] = True
        # Refuse to fall back to the (absent) vendored fmt copy.
        tc.variables["SOCI_FMT_BUILTIN"] = False
        for backend in DISABLED_BACKENDS:
            tc.variables["SOCI_{}".format(backend)] = False
        tc.variables["SOCI_SQLITE3"] = True
        tc.variables["SOCI_EMPTY"] = True
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Run SOCI's Catch2 suite and report the measured numbers.

        ctest registers one test per enabled backend (so two here); each one is
        a Catch2 binary that runs many test cases.  Both numbers are taken from
        the run itself: the ctest summary and, for the SQLite3 binary, the
        "All tests passed (N assertions in M test cases)" line Catch2 prints.
        A non-zero exit fails the build.
        """
        log = os.path.join(self.build_folder, "upstream-tests.log")
        # env="conanrun": fmt and sqlite3 are shared libraries, so the test
        # binaries need Conan's run environment (LD_LIBRARY_PATH) to start at
        # all -- without it the loader reports
        #   "Error loading shared library libfmt.so.11" and ctest sees a
        #   process that never ran.
        self.run(
            'ctest --output-on-failure > "{log}" 2>&1; echo "EXIT=$?" >> "{log}"'.format(log=log),
            cwd=self.build_folder, env="conanrun")

        with open(log, "r", errors="replace") as handle:
            text = handle.read()

        exit_code = None
        for line in text.splitlines():
            if line.startswith("EXIT="):
                exit_code = line[5:].strip()

        ctest_failed = ctest_total = None
        match = re.search(r"(\d+)% tests passed, (\d+) tests failed out of (\d+)", text)
        if match:
            ctest_failed = int(match.group(2))
            ctest_total = int(match.group(3))

        # Catch2's own count from the SQLite3 binary, run directly so its
        # output is not swallowed by ctest on success.
        catch_line = ""
        try:
            catch_out = os.path.join(self.build_folder, "catch-sqlite3.log")
            self.run(
                '"{bin}" ":memory:" > "{out}" 2>&1'.format(
                    bin=os.path.join(self.build_folder, "bin", "soci_sqlite3_test"),
                    out=catch_out),
                cwd=self.build_folder, env="conanrun")
            with open(catch_out, "r", errors="replace") as handle:
                catch_text = handle.read()
            m = re.search(r"All tests passed \((\d+) assertions in (\d+) test cases\)", catch_text)
            if m:
                catch_line = "{} assertions in {} Catch2 test cases".format(m.group(1), m.group(2))
            else:
                catch_line = "Catch2 summary not found (see {})".format(catch_out)
        except ConanException as exc:  # pragma: no cover - diagnostic only
            catch_line = "direct run failed: {}".format(exc)

        self.output.info(
            "soci upstream tests: ctest {}/{} passed, {} failed (exit {}); sqlite3 backend: {}".format(
                (ctest_total or 0) - (ctest_failed or 0), ctest_total, ctest_failed,
                exit_code, catch_line))

        if exit_code != "0" or (ctest_failed is not None and ctest_failed != 0):
            raise ConanException(
                "soci upstream tests failed: ctest exit={} failed={} (of {}); "
                "full log: {}".format(exit_code, ctest_failed, ctest_total, log))

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # .la files carry absolute build paths and are of no use to consumers
        from conan.tools.files import rm
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        # A single target rather than cpp_info.components: soci installs one
        # library per enabled backend plus the core, and naming a component
        # "sqlite3" collides with the sqlite3 *dependency* package in
        # components[].requires -- Conan resolved the bare "sqlite3" to the
        # component itself and reported "sqlite3 requires sqlite3" as a
        # dependency loop.  With plain cpp_info the sqlite3 dependency is
        # linked transitively by Conan, as usual.
        #
        # Order matters for static archives: a library must precede the ones it
        # depends on, and both backends depend on soci_core.
        self.cpp_info.libs = ["soci_sqlite3", "soci_empty", "soci_core"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("pkg_config_name", "soci")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
