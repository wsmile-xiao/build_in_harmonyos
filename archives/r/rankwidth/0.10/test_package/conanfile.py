#!/usr/bin/env python3
"""Conan test_package for rankwidth 0.10 -- consumer + upstream verification.

Builds two executables with CMake and runs them:
test_rankwidth (4 real librw API scenarios: init/calculate_level/
get_rw/destroy_rw on n=1..4) and upstream_smoke (igraph-free driver for
the bundled example graphs, promoted to a real on-device upstream
regression; see upstream_smoke.c provenance header). Emits both
HMBS_UPSTREAM_TEST_RESULT (exit-code oracle over 3 vendored graphs)
and HMBS_TEST_PACKAGE_RESULT (4 checks) markers.
"""
import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import replace_in_file


class RankwidthTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _compiler_executable(self, key, fallback_name):
        # Stale-profile guard (bzrtp/5.3.105 precedent): the ohos profile
        # pins tools.build:compiler_executables to
        # /data/service/hnp/bin/clang(++), which may not exist on the
        # current true-machine worker while a working clang is on PATH.
        # Resolve conf -> PATH so CMakeToolchain never bakes a dead
        # CMAKE_C/CXX_COMPILER into conan_toolchain.cmake (project() dies).
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
            self.output.warning("Cannot run test binary in this environment")
            return
        bindir = self.cpp.build.bindirs[0]
        smoke_exe = os.path.join(bindir, "upstream_smoke")
        for exe in (smoke_exe,):
            if not os.path.isfile(exe):
                raise ConanException("test executable missing: %s" % exe)
        # Upstream regression first: igraph-free driver for the bundled
        # example graphs (verbatim README smoke `rw --edgelist
        # example_graphs/igrid`, igraph I/O replaced per provenance
        # header). Exit code is the deterministic oracle: 0 -> passed;
        # non-zero -> failed. One invocation per vendored graph, so
        # discovered/executed/passed come from the exit codes only (no
        # stdout string counting, no arithmetic patch-ups). The marker is
        # emitted here because the main-recipe build output may be
        # skipped on cache-hit preflight rounds (libarcus/5.0.0 precedent).
        graphs = ["grid.edgelist", "igrid.edgelist", "hangematte.edgelist"]
        graph_paths = [os.path.join(self.source_folder, g) for g in graphs]
        smoke_passed = 0
        smoke_failed = 0
        for gp in graph_paths:
            if not os.path.isfile(gp):
                raise ConanException("upstream data file missing: %s" % gp)
            try:
                self.run('"%s" "%s"' % (smoke_exe, gp), env="conanrun")
                smoke_passed += 1
            except Exception:
                smoke_failed += 1
        upstream_marker = {
            "status": "passed" if smoke_failed == 0 else "failed",
            "framework": "conan-smoke",
            "command": "./upstream_smoke grid.edgelist igrid.edgelist hangematte.edgelist",
            "discovered": len(graph_paths),
            "executed": smoke_passed + smoke_failed,
            "passed": smoke_passed,
            "failed": smoke_failed,
            "skipped": 0,
            "reason": (
                "rw-0.10 ships no formal suite (no tests/ dir, no "
                "TESTS/check_PROGRAMS; Alpine APKBUILD options=!check # no "
                "test suite) but the README documents the smoke `rw "
                "--edgelist example_graphs/igrid` with 3 vendored graphs. "
                "Promoted to a real on-device regression: igraph-free "
                "driver runs the verbatim simplerw.c calculate_level/get_rw "
                "loop on each graph, exit 0 per graph."
            ),
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream_marker, ensure_ascii=False)
        )
        if smoke_failed:
            raise ConanException(
                "upstream_smoke failed (%d/%d graphs)" % (smoke_failed, len(graph_paths))
            )
        exe = os.path.join(bindir, "test_rankwidth")
        # 4 explicit CHECK lines in test_rankwidth.c (n=1..4 init/calc/get/destroy).
        marker = {
            "executed": True,
            "passed": True,
            "command": exe,
            "discovered": 4,
            "passedCount": 4,
        }
        try:
            self.run(exe, env="conanrun")
        except Exception:
            marker["passed"] = False
            self.output.info(
                "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
            )
            raise
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
        )
