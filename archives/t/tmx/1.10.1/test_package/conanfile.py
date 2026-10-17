#!/usr/bin/env python3
"""Conan consumer test for tmx 1.10.1 (upstream ships no test suite)."""
import json
import os
import re
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import replace_in_file


class TmxTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    exports_sources = "CMakeLists.txt", "test_tmx.c"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _compiler_executable(self, key, fallback_name):
        # Same worker-skew as the library recipe: the ohos-aarch64 profile
        # pins tools.build:compiler_executables to
        # /data/service/hnp/bin/clang(++), which may not exist on the
        # current preflight worker. Resolve to an existing binary, else
        # fall back to a PATH lookup (hmbs prepends its tool dirs).
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
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        if str(self.settings.get_safe("os")) == "OHOS":
            tc.cache_variables["CMAKE_C_COMPILER"] = self._compiler_executable(
                "c", "clang"
            )
            tc.cache_variables["CMAKE_CXX_COMPILER"] = self._compiler_executable(
                "cpp", "clang++"
            )
        tc.generate()
        if str(self.settings.get_safe("os")) == "OHOS":
            self._patch_cmake_toolchain_compilers()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        # Serialize the consumer build (same Signal 9 preflight): cap peak
        # fork/memory pressure with an explicit -j1; test sources and
        # flags are unchanged.
        cmake.build(cli_args=["-j1"])

    def test(self):
        # Upstream tmx_1.10.1 provides no automated tests (see
        # test_package/MANIFEST.yml for the audit); report the no_tests
        # marker so rule4 counts stay exact.
        upstream_result = {
            "status": "no_tests",
            "framework": "none",
            "command": "N/A (baylej/tmx tag tmx_1.10.1 has no test entrypoint)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "Tag tmx_1.10.1 contains src/, examples/ (game-engine "
                "demos needing allegro/sdl/raylib, plus a dumper demo "
                "without assertions), doc/ and no tests/ directory; "
                "CMakeLists.txt has no enable_testing/add_test and the "
                "only 'test' hit is .github/workflows/buildandtest.yaml, "
                "a CI filename. Zero automated tests upstream."
            ),
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT="
            + json.dumps(upstream_result, ensure_ascii=False)
        )

        executable = os.path.join(
            self.cpp.build.bindirs[0],
            "test_tmx",
        )
        # 15 deterministic checks in test_tmx.c (see the CHECK list there);
        # the binary exits non-zero unless all 15 pass and always prints
        # a single authoritative summary line "PASSED <passed>/<total>"
        # from its own g_passed/g_total counters. That line is the sole
        # counting source for the marker below: discovered=total,
        # passedCount=passed. No substring counting, no arithmetic
        # repair branches (catch2 lesson). On a shortfall the marker
        # carries a test_failure gap with the FAIL lines as evidence.
        log_path = os.path.join(self.build_folder, "test_tmx_output.log")
        try:
            if os.path.isfile(log_path):
                os.remove(log_path)
        except Exception:
            pass
        run_failed = False
        try:
            self.run(
                '"{}" > "{}" 2>&1'.format(executable, log_path),
                env="conanrun",
            )
        except Exception:
            run_failed = True
        try:
            with open(log_path, encoding="utf-8", errors="replace") as f:
                log_text = f.read()
        except Exception as e:
            failed_marker = {
                "executed": True,
                "passed": False,
                "command": "./test_tmx",
                "discovered": 15,
                "passedCount": 0,
                "gaps": [
                    {
                        "count": 15,
                        "category": "test_failure",
                        "detail": "test log unreadable, cannot confirm checks",
                        "evidence": "open %s failed: %s" % (log_path, e),
                    }
                ],
            }
            self.output.info(
                "HMBS_TEST_PACKAGE_RESULT="
                + json.dumps(failed_marker, ensure_ascii=False)
            )
            # Echo the raw log so preflight keeps the real harness output.
            try:
                self.output.info("test_tmx log missing/unreadable")
            except Exception:
                pass
            raise
        # Re-emit the harness output so preflight logs keep ok/FAIL lines.
        for line in log_text.splitlines():
            self.output.info("test_tmx: %s" % line)
        m = re.search(r"^PASSED\s+(\d+)\s*/\s*(\d+)\s*$", log_text, re.M)
        if m is None:
            failed_marker = {
                "executed": True,
                "passed": False,
                "command": "./test_tmx",
                "discovered": 15,
                "passedCount": 0,
                "gaps": [
                    {
                        "count": 15,
                        "category": "test_failure",
                        "detail": "no PASSED summary line in test output",
                        "evidence": "searched %s for ^PASSED <passed>/<total>; tail: %s"
                        % (log_path, log_text[-500:]),
                    }
                ],
            }
            self.output.info(
                "HMBS_TEST_PACKAGE_RESULT="
                + json.dumps(failed_marker, ensure_ascii=False)
            )
            from conan.errors import ConanException

            raise ConanException("test_tmx produced no PASSED summary line")
        passed_count = int(m.group(1))
        total_count = int(m.group(2))
        # Self-check the single-source identity before emitting.
        assert total_count >= 0 and passed_count >= 0
        assert passed_count <= total_count
        ok = (not run_failed) and (passed_count == total_count)
        consumer_result = {
            "executed": True,
            "passed": ok,
            "command": "./test_tmx",
            "discovered": total_count,
            "passedCount": passed_count,
        }
        if not ok:
            fail_lines = [
                ln
                for ln in log_text.splitlines()
                if ln.startswith("FAIL ")
            ]
            evidence = "; ".join(fail_lines[:5]) or log_text[-500:]
            consumer_result["gaps"] = [
                {
                    "count": total_count - passed_count,
                    "category": "test_failure",
                    "detail": "test_tmx checks failed (binary exit non-zero or shortfall)",
                    "evidence": evidence,
                }
            ]
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT="
            + json.dumps(consumer_result, ensure_ascii=False)
        )
        if not ok:
            from conan.errors import ConanException

            raise ConanException(
                "test_tmx failed: PASSED %d/%d" % (passed_count, total_count)
            )
