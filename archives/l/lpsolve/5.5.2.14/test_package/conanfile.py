#!/usr/bin/env python3
"""Consumer test for the packaged lpsolve library and lp_solve CLI."""

import json
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import replace_in_file


class LpsolveTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

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
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_C_COMPILER"] = self._compiler_executable("c", "clang")
        tc.cache_variables["CMAKE_CXX_COMPILER"] = self._compiler_executable("cpp", "clang++")
        tc.generate()
        self._patch_cmake_toolchain_compilers()
        VirtualRunEnv(self).generate()

    def build(self):
        os.environ["CC"] = self._compiler_executable("c", "clang")
        os.environ["CXX"] = self._compiler_executable("cpp", "clang++")
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _relay_upstream_result(self):
        # Re-emit the build-phase upstream result from the single deterministic
        # source (package share file). Never fabricate counts here: if the
        # relay file is absent (e.g. package built before the suite was wired
        # in), report an explicit failure instead of a no_tests claim.
        relay = None
        try:
            dependency = self.dependencies["lpsolve"]
            relay = os.path.join(
                dependency.package_folder, "share", "lpsolve", "hmbs_upstream_result.json"
            )
        except Exception:
            relay = None
        if relay and os.path.isfile(relay):
            with open(relay, "r", encoding="utf-8", errors="replace") as handle:
                upstream = json.load(handle)
            self.output.info(
                "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
            )
            return
        fallback = {
            "status": "failed",
            "framework": "upstream-unittest-harness",
            "command": "./upstream_test",
            "discovered": 48,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 48,
            "reason": "Upstream result relay file absent from lpsolve package "
            "(share/lpsolve/hmbs_upstream_result.json); build phase did not "
            "record the UnitTest suite run.",
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(fallback, ensure_ascii=False))

    def test(self):
        test_pkg = {
            "executed": True,
            "passed": True,
            "command": "./test_lpsolve && ./test_lpsolve --fault-missing-model && lp_solve -h",
            "discovered": 3,
            "passedCount": 3,
        }
        if not can_run(self):
            test_pkg["executed"] = False
            test_pkg["passed"] = False
            test_pkg["passedCount"] = 0
            test_pkg["command"] = "can_run=false, consumer test skipped"
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))
            self._relay_upstream_result()
            return
        try:
            executable = os.path.join(self.cpp.build.bindirs[0], "test_lpsolve")
            self.run(executable, env="conanrun")
            self.run("%s --fault-missing-model" % executable, env="conanrun")
            dependency = self.dependencies["lpsolve"]
            command = os.path.join(
                dependency.package_folder,
                dependency.cpp_info.bindirs[0],
                "lp_solve",
            )
            self.run('"%s" -h' % command, env="conanrun")
        except Exception:
            test_pkg["passed"] = False
            test_pkg["passedCount"] = 0
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))
            self._relay_upstream_result()
            raise
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))
        self._relay_upstream_result()
