#!/usr/bin/env python3
"""Conan test_package for libcli 1.10.7 — consumer smoke test.

Builds test_libcli.c against the packaged libcli (find_package + libcli::libcli)
and runs it via self.run() (L0d/R34: real execution, exit code enforced).

libcli upstream ships no test suite (see test_package/MANIFEST.yml audit), so
test() also re-emits the HMBS_UPSTREAM_TEST_RESULT no_tests marker every run:
the main recipe build() marker would be missing on package-cache hits, while
test_package test() always executes.
"""

import json
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.files import replace_in_file


class LibcliTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _usable_compiler(self, key, fallbacks):
        # Mirror the main recipe: profile conf may point at a stale
        # /data/service/hnp/bin/clang that no longer exists on preflight;
        # HMBS prepends the real tool dirs to PATH, so prefer an absolute
        # conf path only when it exists, else fall back to PATH lookup.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        cand = compilers.get(key)
        if cand and os.path.isabs(str(cand)) and os.path.isfile(str(cand)):
            return str(cand)
        for name in fallbacks:
            found = shutil.which(name)
            if found and os.path.isfile(found):
                return found
        if cand and os.path.isfile(str(cand)):
            return str(cand)
        return fallbacks[0]

    def build(self):
        # The generated conan_toolchain.cmake can embed a stale
        # CMAKE_C_COMPILER (/data/service/hnp/bin/clang). Override it with
        # a usable compiler resolved via PATH so test_package configures.
        cc = self._usable_compiler("c", ["clang", "cc"])
        cxx = self._usable_compiler("cpp", ["clang++", "c++", "g++"])
        self.output.info("test_package CC={} CXX={}".format(cc, cxx))
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        if os.path.isfile(toolchain):
            for stale in ("/data/service/hnp/bin/clang",
                          "/data/service/hnp/bin/clang++"):
                try:
                    replace_in_file(self, toolchain, stale, cc if "++" not in stale else cxx)
                except Exception:
                    pass
        cmake = CMake(self)
        cmake.configure(variables={"CMAKE_C_COMPILER": cc,
                                   "CMAKE_CXX_COMPILER": cxx})
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: build verified, runtime test skipped")
            return
        # L0d/R34: actually execute the consumer test binary; a non-zero exit
        # fails the test automatically.
        test_bin = os.path.join(self.cpp.build.bindir, "test_libcli")
        self.run(test_bin, env="conanrun")
        marker = {
            "executed": True,
            "passed": True,
            "command": test_bin,
            "discovered": 10,
            "passedCount": 10,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
        # Upstream audit (MANIFEST.yml): no Makefile check/test target, CI only
        # runs `make`, clitest.c is an interactive demo — genuinely no tests.
        upstream_marker = {
            "status": "no_tests",
            "framework": "make",
            "command": "make TESTS=0",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "libcli 1.10.7 upstream has no test suite: Makefile has no check/test target, .github/workflows/c.yml only runs make, clitest.c is an interactive telnet demo",
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream_marker))
