#!/usr/bin/env python3
"""Conan consumer test for libgcrypt20 1.12.2."""

import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import replace_in_file


class Libgcrypt20TestPackage(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _compiler_executable(self, key, fallback_name):
        executables = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        configured = executables.get(key)
        if configured and os.path.isfile(configured):
            return configured
        found = shutil.which(fallback_name)
        return found or configured or fallback_name

    def _patch_cmake_toolchain_compilers(self):
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        replacements = {
            "/data/service/hnp/bin/clang++": self._compiler_executable("cpp", "clang++"),
            "/data/service/hnp/bin/clang": self._compiler_executable("c", "clang"),
        }
        for old, new in replacements.items():
            replace_in_file(self, toolchain, old, new, strict=False)

    def generate(self):
        # Profile pins /data/service/hnp/bin/clang(++) which is absent on
        # current preflight workers (CMake project() fails). Resolve to an
        # existing binary and force via cache variables + toolchain patch.
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        if str(self.settings.get_safe("os")) == "OHOS":
            tc.cache_variables["CMAKE_C_COMPILER"] = self._compiler_executable("c", "clang")
            tc.cache_variables["CMAKE_CXX_COMPILER"] = self._compiler_executable(
                "cpp", "clang++"
            )
        tc.generate()
        if str(self.settings.get_safe("os")) == "OHOS":
            self._patch_cmake_toolchain_compilers()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning("Cross build: consumer execution skipped")
            return
        test_bin = os.path.join(self.cpp.build.bindirs[0], "libgcrypt20_consumer")
        cases = (
            "version",
            "sha256",
            "sha512",
            "sha3-256",
            "hmac-sha256",
            "cmac-aes",
            "aes128-ecb-encrypt",
            "aes128-ecb-decrypt",
            "aes256-cbc",
            "chacha20",
            "pbkdf2-sha256",
            "mpi-add",
            "mpi-mod",
            "sexp",
            "nonce",
        )
        command = "libgcrypt20_consumer 15 cases"
        result = {
            "executed": True,
            "passed": False,
            "command": command,
            "discovered": len(cases),
            "passedCount": 0,
        }
        passed = 0
        try:
            for case in cases:
                self.run(
                    '"{}" {}'.format(test_bin, case),
                    env="conanrun",
                    cwd=self.build_folder,
                )
                passed += 1
        except Exception:
            result["passedCount"] = passed
            fail_line = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(result, ensure_ascii=False)
            print(fail_line, flush=True)
            self.output.info(fail_line)
            raise
        result["passed"] = True
        result["passedCount"] = passed
        tp_line = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(result, ensure_ascii=False)
        print(tp_line, flush=True)
        self.output.info(tp_line)
        # Re-emit upstream evidence persisted by build() into
        # <package>/res/upstream_test_result.json. conan skips build()
        # on cache-hit rounds ("Already installed!"), so this guarantees
        # HMBS_UPSTREAM_TEST_RESULT is present on every run with the real
        # device-run numbers (cxxtest/python3-cairo precedent).
        dep = self.dependencies["libgcrypt20"]
        result_path = os.path.join(dep.package_folder, "res", "upstream_test_result.json")
        if not os.path.isfile(result_path):
            raise ConanException(
                "upstream_test_result.json not found in package (%s); "
                "upstream tests did not run during build()" % result_path)
        with open(result_path, "r", encoding="utf-8") as handle:
            upstream = json.load(handle)
        for key in ("status", "framework", "command", "discovered",
                    "executed", "passed", "failed", "skipped"):
            if key not in upstream:
                raise ConanException("upstream_test_result.json missing key %r" % key)
        if upstream.get("skipped", 0) != 0:
            raise ConanException(
                "upstream_test_result.json has skipped=%r; hard gate requires 0" % (
                    upstream.get("skipped"),))
        if upstream.get("executed") != upstream.get("discovered"):
            raise ConanException(
                "upstream_test_result.json executed != discovered (%r != %r)" % (
                    upstream.get("executed"), upstream.get("discovered")))
        # rule4: 39/41 not 100% must carry gaps with sum == total - passed.
        total = upstream.get("total_upstream_cases")
        if total is not None:
            gaps = upstream.get("gaps")
            if not gaps:
                raise ConanException(
                    "upstream_test_result.json missing gaps for %r/%r partial pass" % (
                        upstream.get("passed"), total))
            gap_sum = sum(int(g.get("count", 0)) for g in gaps)
            if gap_sum != total - upstream.get("passed", 0):
                raise ConanException(
                    "upstream_test_result.json gaps sum %r != total-passed %r" % (
                        gap_sum, total - upstream.get("passed", 0)))
            for g in gaps:
                if g.get("category") not in ("environment", "ohos_feature", "test_failure"):
                    raise ConanException(
                        "upstream_test_result.json gaps category %r not allowed" % (
                            g.get("category"),))
        line = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
        print(line, flush=True)
        self.output.info(line)
