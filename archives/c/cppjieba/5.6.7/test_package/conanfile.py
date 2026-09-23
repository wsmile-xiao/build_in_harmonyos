#!/usr/bin/env python3
"""Test package for cppjieba 5.6.7 (header-only + dict data)."""

import json
import os
import re
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class CppjiebaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        try:
            dep = self.dependencies[self.tested_reference_str]
            dict_dir = os.path.join(dep.package_folder, "share", "cppjieba", "dict")
        except Exception:
            dict_dir = ""
        tc.cache_variables["CPPJIEBA_DICT_DIR"] = dict_dir.replace("\\", "/")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: skip runtime test")
            return
        # L0d gate: exercise the package through Conan self.run.
        bin_dir = self.cpp.build.bindirs[0]
        test_bin = os.path.join(bin_dir, "test_cppjieba")
        self.run('"{}"'.format(test_bin), env="conanrun")
        # Re-run with captured output to count real assertions for the marker.
        try:
            proc = subprocess.run([test_bin], capture_output=True, text=True, timeout=120,
                                  env=os.environ.copy())
            raw = (proc.stdout or "") + (proc.stderr or "")
        except Exception as e:
            raise RuntimeError("test binary re-run failed: {}".format(e))
        self.output.info(raw[-3000:])
        passed = len(re.findall(r"\[PASS\]", raw))
        failed = len(re.findall(r"\[FAIL\]", raw))
        discovered = 3
        # Falsification: binary must print non-empty segmentation output and
        # the packaged dict files must be non-empty.
        try:
            dep = self.dependencies[self.tested_reference_str]
            dict_file = os.path.join(dep.package_folder, "share", "cppjieba", "dict",
                                     "jieba.dict.utf8")
            if os.path.isfile(dict_file):
                size = os.path.getsize(dict_file)
                self.output.info("packaged jieba.dict.utf8 size: {}".format(size))
                if size < 1000:
                    failed += 1
            if "Segmentation output:" not in raw:
                self.output.warning("missing segmentation evidence")
                failed += 1
        except Exception as e:
            self.output.warning("dict check failed: {}".format(e))
        executed = passed + failed
        ok = passed == discovered and failed == 0
        test_pkg = {
            "executed": True,
            "passed": bool(ok),
            "command": "./test_cppjieba",
            "discovered": discovered,
            "passedCount": passed,
        }
        # Re-emit the upstream ctest result persisted in the package.
        try:
            dep = self.dependencies[self.tested_reference_str]
            cands = [
                os.path.join(dep.package_folder, "res", "upstream_test_result.json"),
                os.path.join(dep.package_folder, "upstream_test_result.json"),
            ]
            emitted = False
            for cand in cands:
                if os.path.isfile(cand):
                    with open(cand, "r", encoding="utf-8") as f:
                        up = json.load(f)
                    self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(up, ensure_ascii=False))
                    if up.get("status") != "passed":
                        raise RuntimeError("upstream result not passed: {}".format(up))
                    emitted = True
                    break
            if not emitted:
                self.output.warning("upstream_test_result.json not found in package")
        except Exception as e:
            self.output.warning("upstream re-emit failed: {}".format(e))
            raise
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))
        if not ok:
            raise RuntimeError("test_package failed: {}/{} passed, raw: {}".format(passed, discovered, raw[-1000:]))
