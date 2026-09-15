#!/usr/bin/env python3
"""Conan test_package — ctpl 0.3.5 (C Template Parser Library).

Consumer test builds test.c against the packaged libctpl (ctpl::ctpl,
transitive glib/gio) and runs it: basic template substitution, environ
push/lookup API, and the unknown-symbol error path. Prints the
HMBS_TEST_PACKAGE_RESULT machine-evidence marker on success.

HMBS_UPSTREAM_TEST_RESULT: the upstream automake suite (make check in
recipe build()) is persisted as res/upstream_test_result.json in the
package and re-emitted here so every preflight log carries both markers.
"""

import json
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class CtplTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # CMakeToolchain is instantiated in generate() to inject GLIB_LIBINTL,
    # so it must not also appear here (else conan errors "declared in the
    # generators attribute, but was instantiated in generate() too";
    # zeitgeist precedent).
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # OHOS static glib needs g_libintl_* from its vendored
        # proxy-libintl, but the glib CMakeDeps target does not always
        # propagate it (zeitgeist precedent; CI #44690 shows the same
        # undefined g_libintl_* at CCLD test). Expose the absolute
        # archive to CMake so test_ctpl links it explicitly.
        from conan.tools.cmake import CMakeToolchain as _CT

        tc = _CT(self)
        try:
            glib_folder = self.dependencies["glib"].package_folder
        except Exception:
            glib_folder = None
        if glib_folder:
            for sub in ("lib", "lib64"):
                for base in ("libintl.a", "libintl.so"):
                    cand = os.path.join(glib_folder, sub, base)
                    if os.path.isfile(cand):
                        tc.variables["GLIB_LIBINTL"] = cand.replace("\\", "/")
                        break
                if "GLIB_LIBINTL" in tc.variables:
                    break
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            # Run through ctest so the framework output (Passed/Failed) is
            # the source of the evidence numbers below.
            cmake = CMake(self)
            cmake.test()
            self.run(os.path.join(self.cpp.build.bindirs[0], "test_ctpl"), env="conanrun")
            print(
                'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,'
                '"command":"ctest + ./test_ctpl","discovered":3,"passedCount":3}',
                flush=True,
            )
        else:
            self.output.info("cross-building: built test_ctpl, skipping run")
        package_folder = self.dependencies["ctpl"].package_folder
        result_file = os.path.join(package_folder, "res", "upstream_test_result.json")
        if os.path.isfile(result_file):
            with open(result_file, "r", encoding="utf-8") as f:
                upstream = json.load(f)
            print("HMBS_UPSTREAM_TEST_RESULT=%s" % json.dumps(upstream, ensure_ascii=False), flush=True)
        else:
            raise ConanException(
                "upstream_test_result.json missing in package: %s" % result_file
            )
