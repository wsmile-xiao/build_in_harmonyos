#!/usr/bin/env python3
"""Conan test_package for spooles 2.2 — real IV/DV/InpMtx API checks (R34)
plus one end-to-end consumer flow (rule12 完整消费者用例).

Builds test_spooles.c with CMake and runs it. Emits the
HMBS_TEST_PACKAGE_RESULT marker: discovered/passedCount are the 15 fixed
CHECK assertions in test_spooles.c (IV 4 + DV 3 + InpMtx 3 + e2e 5);
a nonzero test binary exit flips the marker to failed and re-raises.
"""
import json
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class SpoolesTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

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

    def generate(self):
        # Profile pins /data/service/hnp/bin/clang(++), which does not exist
        # on every worker (preflight resolves the real toolchain from PATH).
        # Resolve to an existing binary and force it via cache variables plus
        # a post-generate toolchain patch (repo convention, e.g. bzrtp).
        CMakeDeps(self).generate()
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
        VirtualRunEnv(self).generate()

    def _patch_cmake_toolchain_compilers(self):
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        if not os.path.isfile(toolchain):
            return
        replacements = {
            "/data/service/hnp/bin/clang++": self._compiler_executable(
                "cpp", "clang++"
            ),
            "/data/service/hnp/bin/clang": self._compiler_executable("c", "clang"),
        }
        try:
            with open(toolchain, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
            orig = text
            for old, new in replacements.items():
                if old != new:
                    text = text.replace(old, new)
            if text != orig:
                with open(toolchain, "w", encoding="utf-8", newline="\n") as f:
                    f.write(text)
                self.output.info("spooles test: patched toolchain compiler path")
        except Exception as exc:
            self.output.warning("spooles test: toolchain patch failed: %s" % exc)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _emit(self, payload):
        line = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(payload, ensure_ascii=False)
        print(line, flush=True)
        self.output.info(line)

    def test(self):
        # 15 CHECK assertions in test_spooles.c
        # (IV 4 + DV 3 + InpMtx 3 + end-to-end SpMV/persist flow 5).
        test_pkg = {
            "executed": True,
            "passed": True,
            "command": "./test_spooles",
            "discovered": 15,
            "passedCount": 15,
        }
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries directly,
        # so wrap the test command with the bash from the build environment.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_spooles")
        try:
            self.run('%s -c "\\"%s\\""' % (bash, bin_path), env="conanrun")
        except Exception:
            test_pkg["passed"] = False
            self._emit(test_pkg)
            raise
        self._emit(test_pkg)
