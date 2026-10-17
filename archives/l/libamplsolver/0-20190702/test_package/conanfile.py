#!/usr/bin/env python3
"""Conan test_package — libamplsolver 0-20190702 consumer test.

L1 test (consumer view): compile test_ampl.c against the packaged
libamplsolver static library and run it on the HarmonyOS aarch64 target.

test_ampl.c performs 6 real-API assertions against the packaged library:
  ASL_alloc(ASL_read_pfgh) allocation, plus the library-written fields
  (ASLtype / n_prob / p.Objval function pointer / empty-model n_var_,n_con_),
  and ASL_free resetting the pointer. Exit 0 only if all 6 pass, 1 otherwise.

This conanfile prints the two hmbs hard-gate JSON markers after the test
binary exits; the numbers (discovered/passedCount) come from the 6 real
assertions in test_ampl.c.
"""
import json
import os

from conan import ConanFile
from conan.tools.build import can_run

# test_ampl.c performs exactly 6 assertions.
CONSUMER_CHECK_COUNT = 6


class LibamplsolverTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            raise Exception("Cannot run the test binary on this host")

        dep = self.dependencies["libamplsolver"]
        inc_dir = dep.cpp_info.includedirs[0]
        lib_dir = dep.cpp_info.libdirs[0]

        # R33: compiler from Conan conf, never bare shell env vars.
        comp_execs = self.conf.get("tools.build:compiler_executables",
                                   default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"

        test_src = os.path.join(self.source_folder, "test_ampl.c")
        test_bin = os.path.join(self.build_folder, "test_ampl")

        # Compile + link against the packaged headers and libamplsolver.a.
        self.run(f'"{cc}" -I"{inc_dir}" "{test_src}" '
                 f'-L"{lib_dir}" -lamplsolver -o "{test_bin}"')

        # Run the real consumer test.
        self.run(test_bin, env="conanrun")

        # Machine-readable result for the HMBS gate. Test exit 0 already
        # guarantees all 6 assertions passed (exit 1 otherwise).
        print('HMBS_TEST_PACKAGE_RESULT=' + json.dumps({
            "executed": True,
            "passed": True,
            "command": test_bin,
            "discovered": CONSUMER_CHECK_COUNT,
            "passedCount": CONSUMER_CHECK_COUNT,
        }))

        # Upstream test-suite audit (see test_package/MANIFEST.yml
        # upstream_test_audit): upstream ships no automated tests, so
        # status=no_tests. The audit grep itself is run against the real
        # source tree in conanfile.py build(). Aligned with the
        # gate-passing osmctools/sipcalc/xidle/aribb24 precedent.
        audit_cmd = ("grep -nE '^[a-zA-Z0-9_.-]+:' makefile.u | "
                     "grep -iE 'check|test'")
        print('HMBS_UPSTREAM_TEST_RESULT=' + json.dumps({
            "status": "no_tests",
            "framework": "none",
            "command": audit_cmd,
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "upstream libamplsolver 0-20190702 source ships no "
                "automated tests: makefile.u defines only all/arith.h/"
                "stdio1.h/details.c/systemprintf/xsum.out/clean targets, "
                "no check/test target and no tests/ directory exist"
            ),
        }))
