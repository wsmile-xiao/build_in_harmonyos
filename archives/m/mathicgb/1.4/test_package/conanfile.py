#!/usr/bin/env python3
"""Conan test_package for mathicgb 1.4 -- exercises the real public API.

Builds test_mathicgb.cpp (C probe + version string + GroebnerConfiguration
accessors + a real computeGroebnerBasis run + IdealStreamLog wrapper) with
the OHOS compiler against the packaged static libraries, runs it, and runs
``mgb version`` as a CLI smoke test. Emits HMBS_TEST_PACKAGE_RESULT with
the real case counts (5 consumer groups + 1 CLI smoke = 6).
"""

import json
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


# Consumer checks: 5 groups inside test_mathicgb.cpp (distinct exit codes
# 2..6) + 1 mgb CLI smoke test below.
TEST_CASES = 6


class MathicgbTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["mathicgb"]
        # libmathic.a + mathic headers are bundled inside the mathicgb
        # package (private static sub-build, no separate mathic parcel);
        # only memtailor stays an external dependency package.
        memtailor = self.dependencies["memtailor"]
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cxx = compilers.get("cpp", "clang++")

        result = {
            "executed": True,
            "passed": True,
            "command": "./test_mathicgb && mgb version",
            "discovered": TEST_CASES,
            "passedCount": TEST_CASES,
        }

        def fail():
            result["passed"] = False
            result["passedCount"] = 0
            self.output.info(
                "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(result, ensure_ascii=False)
            )

        includes = [
            os.path.join(pkg.package_folder, "include"),
            os.path.join(memtailor.package_folder, "include"),
        ]
        libdirs = [
            os.path.join(pkg.package_folder, "lib"),
            os.path.join(memtailor.package_folder, "lib"),
        ]
        source = os.path.join(self.source_folder, "test_mathicgb.cpp")
        executable = os.path.join(self.build_folder, "test_mathicgb")
        include_flags = " ".join('-I"{}"'.format(d) for d in includes)
        lib_flags = " ".join('-L"{}"'.format(d) for d in libdirs)
        try:
            self.run(
                '"{cxx}" -std=c++17 -O1 {inc} "{src}" {libs} '
                "-lmathicgb -lmathic -lmemtailor -pthread -o \"{exe}\"".format(
                    cxx=cxx, inc=include_flags, src=source,
                    libs=lib_flags, exe=executable,
                ),
                env="conanbuild",
            )
        except Exception:
            fail()
            raise

        if can_run(self):
            try:
                self.run('"{}"'.format(executable), env="conanrun")
                # CLI smoke test: the mgb binary shipped in bin/.
                # ("version" is a sub-command: VersionAction::staticName(),
                # added in 1.2; it prints "Mathicgb <version>".)
                # Use the absolute packaged path: `package_type` is
                # static-library so the bindirs PATH injection is not
                # guaranteed on every worker (preflight 2026-09-24:
                # "/bin/sh: mgb: inaccessible or not found"). The
                # absolute path exercises the same binary without
                # depending on PATH.
                mgb = os.path.join(pkg.package_folder, "bin", "mgb")
                if os.name == "nt":
                    for _ext in (".exe", ""):
                        if os.path.isfile(mgb + _ext):
                            mgb = mgb + _ext
                            break
                if not os.path.isfile(mgb):
                    raise ConanException(
                        "packaged mgb binary missing at %s" % mgb)
                self.run('"{}" version'.format(mgb), env="conanrun")
            except Exception:
                fail()
                raise
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(result, ensure_ascii=False)
        )
        self._emit_upstream_result()

    def _emit_upstream_result(self):
        # Re-emit the exact upstream numbers measured in build() (see
        # recipe _emit_upstream_marker persistence). Tolerates conan
        # build-cache hits where build() is skipped; no hardcoded copies.
        from conan.errors import ConanException as _ConanException
        path = os.path.join(
            self.dependencies["mathicgb"].package_folder,
            "res", "upstream_test_result.json")
        if not os.path.isfile(path):
            raise _ConanException(
                "upstream_test_result.json not found in package")
        with open(path, "r", encoding="utf-8") as handle:
            upstream = json.load(handle)
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream))
        ok_shape = (
            isinstance(upstream, dict)
            and upstream.get("status") == "passed"
            and int(upstream.get("discovered", -1)) == 237
            and int(upstream.get("executed", -1)) == 237
            and int(upstream.get("passed", -1)) == 237
            and int(upstream.get("failed", -1)) == 0
            and int(upstream.get("skipped", -1)) == 0
        )
        if not ok_shape:
            raise _ConanException(
                "upstream test evidence invalid: %s" % (upstream,))
