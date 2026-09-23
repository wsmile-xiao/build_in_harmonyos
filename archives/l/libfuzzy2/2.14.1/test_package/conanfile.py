#!/usr/bin/env python3
"""Conan test_package — libfuzzy2 2.14.1.

Consumer test (R34): compiles and runs test_fuzzy.c against the packaged
libfuzzy (fuzzy_hash_buf / fuzzy_hash_filename / fuzzy_compare). Uses
direct clang invocation (libestr precedent) to avoid CMake find_library
issues on HMDFS. Emits HMBS machine-evidence markers on stdout.
"""

import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException


class Libfuzzy2TestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["libfuzzy2"]
        inc = os.path.join(dep.package_folder, "include")
        lib = os.path.join(dep.package_folder, "lib")
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cand = compilers.get("c")
        # Same dead-absolute-path guard as the main recipe (ladspa-sdk
        # precedent): only trust the conf path if it is a real executable,
        # otherwise fall back to PATH-resolved bare clang.
        if cand and os.path.isfile(cand):
            try:
                cc = cand if os.access(cand, os.X_OK) else "clang"
            except Exception:
                cc = "clang"
        elif cand:
            self.output.warning(
                f"profile compiler '{cand}' missing, falling back to 'clang' via PATH"
            )
            cc = "clang"
        else:
            cc = shutil.which("clang") or "clang"
            # Prefer the bare name on-device so conanbuild.sh PATH wins.
            if cc != "clang" and os.path.isabs(cc):
                cc = "clang"
        src = os.path.join(self.source_folder, "test_fuzzy.c")
        self.run(f'"{cc}" -fPIC -O2 -I"{inc}" "{src}" -o test_fuzzy -L"{lib}" -lfuzzy')

    def test(self):
        discovered = 4
        passed = 0
        binary = os.path.join(self.build_folder, "test_fuzzy")
        # Fallback: some layouts place the binary beside the build folder.
        if not os.path.isfile(binary):
            alt = os.path.join(self.source_folder, "test_fuzzy")
            if os.path.isfile(alt):
                binary = alt
        try:
            self.run(f'"{binary}"', env="conanrun")
            passed = discovered
        except Exception as exc:
            self.output.error(f"test_fuzzy failed: {exc}")

        tp_result = {
            "executed": True,
            "passed": passed == discovered,
            "command": "test_fuzzy (fuzzy_hash_buf/filename/compare, 4 assertions)",
            "discovered": discovered,
            "passedCount": passed,
        }
        print(f"HMBS_TEST_PACKAGE_RESULT={json.dumps(tp_result)}")

        # Upstream ssdeep 2.14.1 ships no automated test suite (audited
        # tarball, see test_package/MANIFEST.yml upstream_tests_exist:
        # false): no tests/ directory, no TESTS/check_PROGRAMS, make check
        # is automake's default empty target, so the honest result is
        # no_tests/0.
        ut_result = {
            "status": "no_tests",
            "framework": "autotools",
            "command": "make check",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "ssdeep-2.14.1.tar.gz audited (sha256 "
                "ff2eabc78106f009b4fb2def2d76fb0ca9e12acf624cbbfad9b3eb390d931313): "
                "no tests/ or test/ directory and no test source files "
                "anywhere in the tree; Makefile.am declares only "
                "bin_PROGRAMS=ssdeep plus lib_LTLIBRARIES=libfuzzy.la with "
                "no TESTS/check_PROGRAMS/check-local; configure.ac has no "
                "AC_CONFIG_TESTDIR or test macros; normal.sh only rebuilds "
                "and test-against-old.sh needs a legacy binary plus host "
                "paths, neither is a runnable suite; make check expands to "
                "automake's default empty target so it executes zero cases"
            ),
        }
        print(f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(ut_result)}")

        if passed != discovered:
            raise ConanException("test_package fuzzy API tests failed")
