#!/usr/bin/env python3
"""Conan recipe for atracdenc 0.2.3 — ATRAC1/ATRAC3/ATRAC3PLUS audio encoder CLI.

Upstream: https://github.com/dcherednik/atracdenc (LGPL-2.1-or-later).
Builds the `atracdenc` command-line encoder.  The upstream gtest suite (6 test
executables, 80 TEST cases) is built and executed via ctest inside build() and
reported through the HMBS_UPSTREAM_TEST_RESULT marker.
"""
import json
import os
import re
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class AtracdencConan(ConanFile):
    name = "atracdenc"
    version = "0.2.3"
    description = "Open source ATRAC1/ATRAC3/ATRAC3PLUS compatible audio encoder (command-line)"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/dcherednik/atracdenc"
    url = ""

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("atracdenc supports Linux/OHOS only")

    def requirements(self):
        # pcm_io_sndfile.cpp includes <sndfile.hh> and links libsndfile
        # RREV pin: conancenter 的 CCI 配方同版本共存时会被优先解析，其
        # tool_requires 拉入 cmake/4.4.2，在 OHOS 上 KeyError 'OHOS'。
        # pin 到本仓适配配方；RREV 以 ohpcd conan v2 API revisions 实测为准
        # （libsndfile 2026-08-20、gtest 2026-08-10 发布，非本地复算）。
        self.requires("libsndfile/1.2.2#cf6ded313ae8c9c830e5ec3d3a8ce497")
        # upstream test/CMakeLists.txt links GTest::gtest_main
        self.test_requires("gtest/1.17.0#ab1bc3bf51522490eef07a83c2dbd203")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: CMake has no HarmonyOS platform module; force the Linux branch so
        # the upstream `if (UNIX)` enables find_package(GTest) + test/ + ctest.
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        # R26: system-name library — static build
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Run the upstream gtest suite via ctest and emit HMBS_UPSTREAM_TEST_RESULT."""
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        cmd = "ctest --output-on-failure -V -j1"
        proc = subprocess.run(
            [bash, "-c", cmd],
            cwd=self.build_folder,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=1800,
        )
        output = proc.stdout
        # gtest summary lines: "[  PASSED  ] N tests" / "[  FAILED  ] M tests"
        passed = sum(int(m) for m in re.findall(r"\[  PASSED  \] (\d+) tests", output))
        failed = sum(int(m) for m in re.findall(r"\[  FAILED  \] (\d+) tests", output))
        executed = passed + failed
        discovered = executed
        if executed == 0:
            # fall back to ctest-level counts if gtest summaries were not emitted
            m = re.search(r"(\d+) tests out of (\d+)", output)
            if m:
                discovered = int(m.group(2))
                executed = int(m.group(1))
                passed = executed - failed
        status = "passed" if proc.returncode == 0 and failed == 0 and executed > 0 else "failed"
        marker = {
            "status": status,
            "framework": "ctest",
            "command": "ctest --output-on-failure -V -j1",
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False))
        if status != "passed":
            self.output.error("upstream tests failed; tail:\n" + output[-2000:])
            raise RuntimeError("upstream tests failed")

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
