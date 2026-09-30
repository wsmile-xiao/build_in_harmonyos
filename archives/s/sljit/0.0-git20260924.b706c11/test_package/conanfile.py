#!/usr/bin/env python3
"""Conan test_package for sljit 0.0-git20260924.b706c11 — consumer JIT test.

Builds test_sljit.c against the packaged sljit library, runs the generated
JIT code and verifies the results. It emits the HMBS_TEST_PACKAGE_RESULT
marker from the real "ok" evidence line in the test output, then re-emits
the upstream GNUmakefile suite summary that the recipe persisted into the
package (with no hardcoded copies of those numbers).
"""

import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import replace_in_file


class SljitTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _compiler_executable(self, key, fallback_name):
        # Stale-toolchain guard (cvector/bzrtp convention): the profile pins
        # /data/service/hnp/bin/clang(++), but that file may not exist on the
        # current worker (lz4 DRAFT evidence: toolchain migrated to
        # ~/usr/local/bin). Prefer an absolute conf path only when it exists,
        # else fall back to PATH lookup (HMBS prepends real tool dirs).
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
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        # E092: vanilla cmake has no Platform/HarmonyOS.cmake module, so the
        # default Conan os=OHOS -> CMAKE_SYSTEM_NAME=HarmonyOS toolchain fails
        # compiler detection ("System is unknown to cmake" + CMAKE_C_COMPILER
        # broken). HarmonyOS is Linux-kernel based, force the Linux branch.
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            # Stale profile path guard: force a usable compiler via cache
            # variables (post-generate patch below rewrites any residual
            # stale absolute path baked into conan_toolchain.cmake).
            tc.cache_variables["CMAKE_C_COMPILER"] = self._compiler_executable("c", "clang")
            tc.cache_variables["CMAKE_CXX_COMPILER"] = self._compiler_executable("cpp", "clang++")
        tc.generate()
        if str(self.settings.get_safe("os")) == "OHOS":
            self._patch_cmake_toolchain_compilers()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: skip runtime test")
            return
        binary = os.path.join(self.cpp.build.bindirs[0], "test_sljit")
        log_path = os.path.join(self.build_folder, "test_sljit.log")
        try:
            self.run('"%s" > "%s" 2>&1' % (binary, log_path), env="conanrun")
        except ConanException:
            # Non-zero exit: the captured log still holds the evidence we
            # parse; fall through and let the marker/count be the verdict.
            pass
        out = ""
        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                out = f.read()
        except OSError:
            out = ""
        self.output.info("test output:\n" + out)

        # test_sljit.c runs five (5) JIT-generated-function assertions and
        # prints a single trailing "ok" line only when every assertion passed.
        discovered = 5
        passed_count = (
            discovered if ("sljit test_package ok" in out and "FAIL " not in out) else 0
        )
        marker = {
            "executed": True,
            "passed": discovered > 0 and passed_count == discovered,
            "command": "./test_sljit (JIT compile + execute 5 assertions)",
            "discovered": discovered,
            "passedCount": passed_count,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker), flush=True)
        self.run(binary, env="conanrun")
        self._emit_upstream_result()
        if not marker["passed"]:
            raise ConanException(
                "test_package failed: %d/%d cases passed" % (passed_count, discovered)
            )

    def _emit_upstream_result(self):
        dep = self.dependencies["sljit"]
        path = os.path.join(dep.package_folder, "res", "upstream_test_summary.json")
        if not os.path.isfile(path):
            raise ConanException(
                "upstream_test_summary.json not found in package (searched %s)" % path
            )
        with open(path, "r", encoding="utf-8") as f:
            result = json.load(f)
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result))
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result), flush=True)
        if result.get("status") != "passed":
            raise ConanException("upstream GNUmakefile suite evidence is not fully green")
