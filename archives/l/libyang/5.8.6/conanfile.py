#!/usr/bin/env python3
"""Conan recipe — libyang 5.8.6 (YANG data modelling library).

libyang is the C library behind most NETCONF/RESTCONF tooling: it parses YANG
and YIN schemas, compiles them into a schema tree, parses instance data in XML/
JSON/LYB, and validates it against the schema.

Build system : CMake (>= 3.22).
Dependencies : **pcre2** (>= 10.21, required by upstream's
               ``find_package(PCRE2 10.21 REQUIRED)``).  ``xxhash`` is optional
               and deliberately not required.  ``cmocka`` is a *test-only*
               dependency, pulled in through ``build_requirements()``.
Package form : a library — ``libyang.so`` / ``libyang.a`` + the headers, plus
               the ``yanglint`` / ``yangre`` tools when ``ENABLE_TOOLS`` is on.

Configuration notes:

  * ``ENABLE_TESTS=ON`` builds upstream's cmocka-based unit tests, which are
    run for real in ``build()``.  This only takes effect for a **shared** build
    — see the note on ``default_options`` below.
  * ``ENABLE_VALGRIND_TESTS=OFF`` and ``ENABLE_FUZZ_TARGETS=OFF``: valgrind is
    not present on the target and fuzzing regression targets are a different
    kind of artefact.
  * ``ENABLE_YANGLINT_INTERACTIVE=OFF``: the interactive yanglint tests are Tcl
    scripts (``tclsh``).  There is no Tcl on the HarmonyOS worker, and without
    this switch upstream would still register tests whose command is the
    ``PATH_TCLSH-NOTFOUND`` placeholder.

Upstream tests — see test_package/MANIFEST.yml for the full audit:
  * 57 ``ly_add_utest()`` entries in tests/CMakeLists.txt, each one cmocka
    binary registered as a CTest case — this is what ``build()`` runs.
  * the yangre / interactive-yanglint suites are Tcl-driven and are therefore
    NOT_RUN on this target (no tclsh), reported with that reason rather than
    counted as passes.  The ``headers`` style check and the three
    ``regress_fuzz_*`` entries need the formatting toolchain and the fuzz
    targets respectively, neither of which is part of a library build.
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, rm


class LibyangConan(ConanFile):
    name = "libyang"
    version = "5.8.6"
    description = ("libyang — YANG data modelling library (parser, schema "
                   "compiler, data validation)")
    license = "BSD-3-Clause"
    homepage = "https://github.com/CESNET/libyang"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "tools": [True, False],
    }
    # ⚠️ shared defaults to True on purpose.  Upstream's CMakeLists disables the
    # whole test suite for static builds:
    #     if(NOT BUILD_SHARED_LIBS)
    #         message(STATUS "Disabling tests for static build")
    #         set(ENABLE_TESTS OFF)
    # so a static package would ship untested.  libyang is not a system
    # same-name library, so R26's static requirement does not apply and Conan
    # manages the dependency chain for the shared build.
    default_options = {
        "shared": True,
        "fPIC": True,
        "tools": True,
    }

    # tests/CMakeLists.txt: one `ly_add_utest(NAME ...)` per cmocka test binary.
    UPSTREAM_UTEST_CASES = 57

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libyang is prepared for Linux/OHOS targets only")

    def requirements(self):
        # upstream: find_package(PCRE2 10.21 REQUIRED)
        self.requires("pcre2/10.47")

    def build_requirements(self):
        # cmocka is only needed to build upstream's own unit tests
        self.test_requires("cmocka/2.0.2")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["ENABLE_TESTS"] = True
        tc.variables["ENABLE_VALGRIND_TESTS"] = False
        tc.variables["ENABLE_FUZZ_TARGETS"] = False
        # Tcl-driven interactive yanglint tests: no tclsh on the target
        tc.variables["ENABLE_YANGLINT_INTERACTIVE"] = False
        tc.variables["ENABLE_TOOLS"] = bool(self.options.tools)
        tc.variables["ENABLE_LYD_PRIV"] = False
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Run upstream's cmocka unit tests and report the measured counts.

        Only the ``utest_*`` cases are selected: those are the 57 CTest entries
        created by ``ly_add_utest()`` in tests/CMakeLists.txt.  The remaining
        upstream test entries are Tcl-driven (guarded off by configuration) or
        source-style checks, and several of them cannot run on this target at
        all — see test_package/MANIFEST.yml.  A non-zero ctest exit fails the
        build; nothing is declared as passing that did not run.
        """
        log = os.path.join(self.build_folder, "upstream-tests.log")
        self.run(
            'ctest -R "^utest_" --output-on-failure --timeout 300 '
            '> "{log}" 2>&1; echo "EXIT=$?" >> "{log}"'.format(log=log),
            cwd=self.build_folder)

        with open(log, "r", errors="replace") as handle:
            text = handle.read()

        exit_code = None
        for line in text.splitlines():
            if line.startswith("EXIT="):
                exit_code = line[5:].strip()

        passed = failed = None
        match = re.search(r"(\d+)% tests passed, (\d+) tests failed out of (\d+)", text)
        if match:
            failed = int(match.group(2))
            total = int(match.group(3))
            passed = total - failed

        self.output.info(
            "libyang upstream utests: {}/{} passed, {} failed (ctest exit {})".format(
                passed, self.UPSTREAM_UTEST_CASES, failed, exit_code))

        if exit_code != "0" or (failed is not None and failed != 0):
            raise ConanException(
                "libyang upstream utests failed: ctest exit={} failed={} (of {}); "
                "full log: {}".format(exit_code, failed, self.UPSTREAM_UTEST_CASES, log))

    def package(self):
        cmake = CMake(self)
        cmake.install()
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["yang"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("pkg_config_name", "libyang")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "m", "dl"]
