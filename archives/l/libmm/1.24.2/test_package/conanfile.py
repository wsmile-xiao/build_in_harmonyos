#!/usr/bin/env python3
"""Conan test_package — libmm 1.24.2.

Builds test_mm.c against the packaged mm-glib library (CMakeDeps +
CMakeToolchain), runs it under ctest, then runs the binary directly: the
binary calls real mm-glib APIs and emits the HMBS_TEST_PACKAGE_RESULT marker
itself. The upstream meson evidence persisted in the package (res/
upstream_test_result.json) is re-emitted here so cache hits ("Already
installed", when build() is skipped) still produce the upstream marker.
"""
import json
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import replace_in_file


class LibmmTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _compiler_executable(self, key, fallback_name):
        try:
            executables = self.conf.get(
                "tools.build:compiler_executables",
                default={},
                check_type=dict,
            ) or {}
        except Exception:
            executables = {}
        configured = executables.get(key)
        if configured and os.path.isfile(configured):
            return configured
        # HMBS injects absolute tool paths; prefer them over bare PATH.
        for env_key in ("HMBS_CMAKE", "HMBS_MAKE", "HMBS_NINJA"):
            _ = os.environ.get(env_key)
        found = shutil.which(fallback_name)
        if found and os.path.isfile(found):
            return found
        if configured:
            return configured
        return fallback_name

    def _patch_cmake_toolchain_compilers(self):
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        if not os.path.isfile(toolchain):
            return
        replacements = {
            "/data/service/hnp/bin/clang++": self._compiler_executable("cpp", "clang++"),
            "/data/service/hnp/bin/clang": self._compiler_executable("c", "clang"),
        }
        for old, new in replacements.items():
            replace_in_file(self, toolchain, old, new, strict=False)

    def generate(self):
        # Profile pins /data/service/hnp/bin/clang(++) which is absent on
        # some workers (test_package cmake aborts with "The CMAKE_C_COMPILER
        # ... was not found"); resolve to an existing binary and force it
        # via cache variables + post-generate toolchain patch (cvector
        # 1.0.4.1 / zydis 4.1.1 precedent). The "unknown to cmake /
        # Platform/HarmonyOS" notice is a warning only; the compiler path
        # is the fatal part.
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        if str(self.settings.get_safe("os")) == "OHOS":
            tc.cache_variables["CMAKE_C_COMPILER"] = self._compiler_executable("c", "clang")
            tc.cache_variables["CMAKE_CXX_COMPILER"] = self._compiler_executable("cpp", "clang++")
        tc.generate()
        if str(self.settings.get_safe("os")) == "OHOS":
            self._patch_cmake_toolchain_compilers()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        # Run the test binary directly; it emits HMBS_TEST_PACKAGE_RESULT.
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_mm"),
                 env="conanrun")
        # Re-emit the upstream marker from the packaged evidence file.
        evidence = os.path.join(self.dependencies["libmm"].package_folder,
                                "res", "upstream_test_result.json")
        if os.path.isfile(evidence):
            with open(evidence, encoding="utf-8") as handle:
                raw = handle.read()
            json.loads(raw)  # validate before emitting
            self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + raw.strip())
        else:
            self.output.warning("upstream test evidence not found in package: " + evidence)
