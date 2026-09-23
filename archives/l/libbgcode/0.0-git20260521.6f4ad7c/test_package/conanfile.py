#!/usr/bin/env python3
"""Conan test_package — libbgcode real consumer verification.

Builds two consumers against the packaged libraries (convert_contract via
LibBGCode::bgcode_convert, core_contract via LibBGCode::bgcode_binarize)
and runs them under ctest. Counts for HMBS_TEST_PACKAGE_RESULT come solely
from this run's Testing/Temporary/LastTest.log (single deterministic
source); any deviation fails instead of guessing.
"""

import json
import os
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LibbgcodeTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        # Same stale-compiler gap as the main recipe (htslib precedent):
        # the profile-pinned /data/service/hnp/bin/clang(++) may not exist
        # on the worker, so rewrite the generated toolchain file before
        # configuring and force working compilers via -D variables.
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        if os.path.isfile(toolchain):
            with open(toolchain, "r", encoding="utf-8", errors="replace") as handle:
                content = handle.read()
            patched = content.replace("/data/service/hnp/bin/clang++", "clang++")
            patched = patched.replace("/data/service/hnp/bin/clang", "clang")
            if patched != content:
                with open(toolchain, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write(patched)
        cmake = CMake(self)
        cmake.configure(variables={
            "CMAKE_C_COMPILER": "clang",
            "CMAKE_CXX_COMPILER": "clang++",
        })
        cmake.build()

    def test(self):
        if not can_run(self):
            raise ConanException("libbgcode test_package must run natively")
        self.run(
            "ctest --output-on-failure",
            cwd=self.build_folder,
            env="conanrun",
            ignore_errors=True,
        )
        log_path = self._find_last_test_log(self.build_folder)
        discovered, passed = self._parse_ctest_log(log_path)
        marker = {
            "executed": discovered > 0,
            "passed": discovered > 0 and passed == discovered,
            "command": "ctest --output-on-failure",
            "discovered": discovered,
            "passedCount": passed,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
        if not marker["passed"]:
            raise ConanException(
                "libbgcode test_package failed: "
                "discovered=%d passedCount=%d (log %s)"
                % (discovered, passed, log_path)
            )

    @staticmethod
    def _find_last_test_log(build_folder):
        """Primary LastTest.log path first, then a capped recursive walk.

        cmake_layout may place the real CTest tree one level below
        build_folder (build/Release); a single fixed path would miss it.
        Returns the richest candidate (most test headers), else the primary
        path (which _parse_ctest_log then reports as missing).
        """
        primary = os.path.join(
            build_folder, "Testing", "Temporary", "LastTest.log")
        candidates = [primary]
        try:
            if os.path.isdir(build_folder):
                base_depth = build_folder.count(os.sep)
                for cur, _dirs, files in os.walk(build_folder):
                    if "LastTest.log" in files:
                        full = os.path.join(cur, "LastTest.log")
                        if full not in candidates:
                            candidates.append(full)
                    if cur.count(os.sep) - base_depth > 6:
                        try:
                            _dirs[:] = []
                        except Exception:
                            pass
        except Exception:
            pass

        def _headers(path):
            try:
                with open(path, "r", encoding="utf-8",
                          errors="replace") as handle:
                    content = handle.read()
            except OSError:
                return -1
            if not content.strip():
                return -1
            return len(re.findall(
                r"(?m)^\s*\d+/\d+\s+Test(?:ing)?:", content))

        best, best_count = primary, -1
        for path in candidates:
            if not os.path.isfile(path):
                continue
            count = _headers(path)
            if count > best_count:
                best, best_count = path, count
        return best

    @staticmethod
    def _parse_ctest_log(log_path):
        """Return (discovered, passed) from a ctest LastTest.log.

        Same single-source format as the main recipe: discovered is the M
        denominator of the per-test `N/M Testing:` / `N/M Test:` headers
        (every entry must agree), passed counts the `Test Passed.` verdict
        footers. ctest never writes stdout-style `N/M Test #K:` lines into
        this file, so matching those here always yields zero. Anything
        else (missing log, malformed headers) yields (0, 0) and the caller
        fails closed; a non-passed entry yields passed < discovered and
        the caller fails as well.
        """
        if not os.path.isfile(log_path):
            return 0, 0
        with open(log_path, "r", encoding="utf-8", errors="replace") as handle:
            content = handle.read()
        try:
            content = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", content)
        except Exception:
            pass
        sizes = set(
            int(match.group(1))
            for match in re.finditer(
                r"(?m)^\s*\d+/(\d+)\s+Test(?:ing)?:", content)
        )
        if len(sizes) != 1:
            return 0, 0
        discovered = sizes.pop()
        if discovered == 0:
            return 0, 0
        passed = len(re.findall(r"Test Passed", content))
        return discovered, passed
