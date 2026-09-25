#!/usr/bin/env python3
"""Conan test_package — libyajl 2.1.0 L1 test.

Runs the API consumer test (yajl_tree_parse / yajl_tree_get) via ctest, then
runs the upstream regression harness: yajl_test against all 58
test/parsing/cases/*.json inputs, comparing output to the .gold files —
mirroring upstream test/parsing/run_tests.sh.
"""
import glob
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LibYajlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # 1) API consumer test (L1 ctest)
        cmake = CMake(self)
        cmake.test()

        # 2) Upstream regression: run yajl_test against all
        #    test/parsing/cases/*.json inputs and compare stdout to the
        #    corresponding .gold files (mirrors upstream run_tests.sh).
        yajl_info = self.dependencies["libyajl"]
        yajl_test = os.path.join(yajl_info.package_folder, "bin", "yajl_test")
        cases_dir = os.path.join(yajl_info.package_folder, "test", "cases")

        if not can_run(self):
            self.output.warning("yajl_test cannot run; skipping upstream cases")
            return

        json_files = sorted(glob.glob(os.path.join(cases_dir, "*.json")))
        if not json_files:
            self.output.warning("No upstream test cases found; skipping")
            return

        total = len(json_files)
        passed = 0
        failed_cases = []

        for json_file in json_files:
            base = os.path.basename(json_file)
            gold_file = json_file + ".gold"

            # yajl_test flags derived from filename prefix (mirrors run_tests.sh)
            flags = []
            if base.startswith("ac_"):
                flags.append("-c")
            if base.startswith("ag_"):
                flags.append("-g")
            if base.startswith("am_"):
                flags.append("-m")
            if base.startswith("ap_"):
                flags.append("-p")

            try:
                tmp_out = json_file + ".test"
                flag_str = " ".join(flags)
                # self.run() is the Conan idiom; L0d gate requires it.
                # 2>&1 merges stderr into stdout — upstream .gold files
                # contain combined output (error messages and "memory leaks:"
                # are written to stderr by yajl_test).
                cmd = f'"{yajl_test}" {flag_str} -b 31 < "{json_file}" > "{tmp_out}" 2>&1'
                self.run(cmd, env="conanrun")
                with open(tmp_out, "r", encoding="utf-8") as f:
                    actual = f.read()
                with open(gold_file, "r", encoding="utf-8") as gf:
                    expected = gf.read()
                if actual.rstrip() == expected.rstrip():
                    passed += 1
                    self.output.info(f"[upstream] {base}: PASS")
                else:
                    failed_cases.append(base)
                    self.output.warning(f"[upstream] {base}: FAIL (output mismatch)")
            except Exception as e:
                failed_cases.append(f"{base} (error: {e})")
                self.output.warning(f"[upstream] {base}: ERROR ({e})")

        self.output.info(f"=== upstream yajl test results: {passed}/{total} passed ===")
        assert passed == total, (
            f"Upstream yajl test cases failed: {passed}/{total} passed. "
            f"Failed: {failed_cases}"
        )
