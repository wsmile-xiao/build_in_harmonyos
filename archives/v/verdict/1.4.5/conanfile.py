#!/usr/bin/env python3
"""Conan recipe for verdict 1.4.5 — Sandia mesh quality metrics library.

Verdict computes quality metrics for 2D/3D finite elements (edge, tri, quad,
tet, hex, wedge, pyramid, knife) in the C++ namespace ``verdict``. Upstream
ships a GoogleTest unit suite (unittests/, 67 TEST cases); this recipe builds
that suite on the target and runs it during ``conan create`` (the real
per-case count is emitted as the HMBS_UPSTREAM_TEST_RESULT marker).

R32 note: no settings.os branch is needed for the toolchain — the OHOS-adapted
conan maps os=OHOS to CMAKE_SYSTEM_NAME=HarmonyOS via CMakeToolchain.
"""
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get, rmdir)


class VerdictConan(ConanFile):
    name = "verdict"
    version = "1.4.5"
    description = ("Verdict - compute quality functions of 2 and 3-dimensional "
                   "finite elements (mesh quality metrics)")
    license = "BSD-3-Clause"
    homepage = "https://github.com/sandialabs/verdict"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def build_requirements(self):
        # unittests/ links GoogleTest; resolve it as a test requirement so the
        # suite is built for (and runs on) the OHOS target.
        self.test_requires("gtest/1.17.0.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["VERDICT_ENABLE_TESTING"] = "ON"
        tc.variables["VERDICT_BUILD_DOC"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Run the upstream GoogleTest suite and emit HMBS_UPSTREAM_TEST_RESULT.

        First through CTest (the upstream-registered runner), then the GTest
        binary directly so the per-case summary can be parsed into a
        machine-readable marker with the real executed/passed counts.
        """
        ctest_rc = None
        ctest = shutil.which("ctest")
        if ctest:
            proc = subprocess.run([ctest, "--output-on-failure"],
                                  cwd=self.build_folder, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, text=True, timeout=1800)
            ctest_rc = proc.returncode
            if ctest_rc != 0:
                self.output.error((proc.stdout or "")[-4000:])

        exe = None
        for root, _dirs, files in os.walk(self.build_folder):
            if "unittests_verdict" in files:
                exe = os.path.join(root, "unittests_verdict")
                break
        if exe is None:
            raise ConanException("unittests_verdict executable not found in build tree")

        proc = subprocess.run([exe], stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True,
                              cwd=os.path.dirname(exe), timeout=1800)
        output = proc.stdout or ""
        ran = re.search(r"\[==========\] (\d+) tests? from (\d+) test suites? ran", output)
        passed = re.search(r"\[  PASSED  \] (\d+) tests?", output)
        failed = re.search(r"\[  FAILED  \] (\d+) tests?", output)
        executed = int(ran.group(1)) if ran else 0
        passed_n = int(passed.group(1)) if passed else 0
        failed_n = int(failed.group(1)) if failed else 0
        status = "passed" if (proc.returncode == 0 and executed > 0
                              and failed_n == 0 and passed_n == executed) else "failed"
        upstream = {
            "status": status,
            "framework": "gtest",
            "command": "./unittests/unittests_verdict",
            "discovered": executed,
            "executed": executed,
            "passed": passed_n,
            "failed": failed_n,
            "skipped": 0,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT="
                         + json.dumps(upstream, ensure_ascii=False))
        if status != "passed" or ctest_rc not in (None, 0):
            self.output.error(output[-4000:])
            raise ConanException("upstream verdict unit tests failed "
                                 f"(ctest rc={ctest_rc})")

    def package(self):
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        # CMake package config files are regenerated by Conan (CMakeDeps);
        # keep the package layout minimal.
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.libs = ["verdict"]
        self.cpp_info.set_property("cmake_file_name", "verdict")
        self.cpp_info.set_property("cmake_target_name", "verdict::verdict")
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
