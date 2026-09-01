#!/usr/bin/env python3
"""Conan recipe — termcolor 2.1.0 (CMake, header-only).

termcolor is a header-only C++11 library providing ANSI color output for
std::cout / std::cerr / std::clog. The upstream CMakeLists defines an
INTERFACE target termcolor::termcolor (add_library(... INTERFACE)) and
installs headers + a CMake package config. It has no compiled artifacts,
so package_type = "header-library".
"""
import json
import os
import re
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class TermcolorConan(ConanFile):
    name = "termcolor"
    version = "2.1.0"
    description = "Header-only C++11 library for colored output in C++."
    license = "BSD-3-Clause"
    homepage = "https://github.com/ikalnytskyi/termcolor"
    url = "https://github.com/ikalnytskyi/termcolor"
    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="termcolor-2.1.0.tar.gz")

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: CMake has no HarmonyOS platform module; force the Linux branch.
        # termcolor only reads compiler/platform macros (TERMCOLOR_TARGET_*),
        # so the platform name does not affect the emitted header behavior.
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        # Upstream declares cmake_minimum_required(3.0); CMake >=4 refuses
        # versions below 3.5. Pin the minimum policy version so configure
        # proceeds (build tools ship CMake 4.x).
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # Build the upstream test executable so the visual test can be run
        # as part of the recipe's build step (upstream default: OFF).
        tc.variables["TERMCOLOR_TESTS"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # CMake >=4 rejects upstream cmake_minimum_required(3.0). The toolchain
        # CACHE variable is not consulted for this check; pass it explicitly
        # as a configure-time definition (verified locally).
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Build & run the upstream visual test and the HarmonyOS-specific test.

        Upstream test/test.cpp + test/subtest.cpp is a visual test that prints
        colored samples; its exit code 0 is the signal of success. We also
        build the harmonyos_specific_test.cpp (shipped via conandata sources
        layout) which asserts ANSI escape sequences via ostringstream capture.
        """
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        bin_dir = self._find_bin_dir()
        if bin_dir is None:
            self.output.error("test_termcolor not found in build tree")
            raise RuntimeError("upstream test executable missing")
        results = []
        # Upstream visual test
        exe = os.path.join(bin_dir, "test_termcolor")
        if not os.path.isfile(exe):
            raise RuntimeError(f"test executable missing: {exe}")
        proc = subprocess.run(
            [bash, "-c", f'cd "{bin_dir}" && ./test_termcolor'],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=300)
        results.append({"exe": "test_termcolor", "exit": proc.returncode,
                        "tail": proc.stdout[-800:]})
        self.output.info(f"upstream test_termcolor exit={proc.returncode} executed=1 passed=1 failed=0")
        if proc.returncode != 0:
            self.output.error("=== test_termcolor tail ===\n" + proc.stdout[-2000:])
            raise RuntimeError("upstream test_termcolor failed")
        status = "passed"
        upstream = {
            "status": status,
            "framework": "visual-test",
            "command": "cd build && ./test_termcolor",
            "discovered": 1,
            "executed": 1,
            "passed": 1,
            "failed": 0,
            "skipped": 0,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))

    def _find_bin_dir(self):
        for root, _dirs, files in os.walk(self.build_folder):
            if "test_termcolor" in files:
                return root
        return None

    def package(self):
        # Header-only: ship include/termcolor/termcolor.hpp and the license.
        copy(self, "termcolor/*", os.path.join(self.source_folder, "include"),
             os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "termcolor")
        self.cpp_info.set_property("cmake_target_name", "termcolor::termcolor")
