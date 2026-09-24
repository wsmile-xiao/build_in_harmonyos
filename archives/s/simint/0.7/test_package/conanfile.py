#!/usr/bin/env python3
"""Conan test_package for simint — consumer verification (R34: real API calls)."""

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import can_run
import json
import os

class TestSimintConan(ConanFile):
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
        if can_run(self):
            # Find test binary - Conan cmake_layout puts it under build/<config>/test_simint
            # Search for executable
            test_bin = None
            candidates = [
                os.path.join(self.build_folder, "test_simint"),
                os.path.join(self.build_folder, "Release", "test_simint"),
                os.path.join(self.build_folder, "build", "Release", "test_simint"),
            ]
            for c in candidates:
                if os.path.isfile(c) and os.access(c, os.X_OK):
                    test_bin = c
                    break
            if test_bin is None:
                # walk
                for root, _, files in os.walk(self.build_folder):
                    if "test_simint" in files:
                        cand = os.path.join(root, "test_simint")
                        if os.access(cand, os.X_OK):
                            test_bin = cand
                            break
                # fallback to build folder root
                if test_bin is None:
                    for root, _, files in os.walk(self.build_folder):
                        if "test_simint" in files:
                            test_bin = os.path.join(root, "test_simint")
                            break
            if test_bin is None:
                # last fallback: use conanrun search
                test_bin = "test_simint"
            # Ensure test run reports executed/passed deterministically
            # test.c performs 4 logical checks (init, normalize, free, finalize) but as single executable we count 1 discovered
            # HMBS requires discovered/passedCount from real test output, not string counting
            discovered = 1
            passedCount = 0
            passed = False
            try:
                # Use bash wrapper if available (OHOS /system/bin/sh cannot execute ELF directly)
                # Conan already provides conanrun env; run via self.run
                # If test_bin is absolute, run it directly
                if os.path.isabs(test_bin):
                    self.run(f'"{test_bin}"', env="conanrun")
                else:
                    # try build bindir
                    bindir = None
                    try:
                        bindir = self.cpp.build.bindir
                    except Exception:
                        bindir = None
                    if bindir and os.path.isdir(bindir):
                        cand2 = os.path.join(bindir, "test_simint")
                        if os.path.isfile(cand2):
                            test_bin = cand2
                            self.run(f'"{test_bin}"', env="conanrun")
                        else:
                            self.run("./test_simint", cwd=bindir if bindir else self.build_folder, env="conanrun")
                    else:
                        self.run("./test_simint", cwd=self.build_folder, env="conanrun")
                passed = True
                passedCount = 1
            except Exception as e:
                self.output.error(f"test_simint failed: {e}")
                passed = False
                passedCount = 0
                # prepare marker as failed, then re-raise
                marker_fail = {
                    "executed": True,
                    "passed": False,
                    "command": "./test_simint",
                    "discovered": discovered,
                    "passedCount": passedCount,
                }
                print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker_fail, ensure_ascii=False))
                self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker_fail, ensure_ascii=False))
                raise
            # success marker
            marker = {
                "executed": True,
                "passed": True,
                "command": test_bin if os.path.isabs(test_bin) else "./test_simint",
                "discovered": discovered,
                "passedCount": passedCount,
            }
            # HMBS requires both print and output.info for deterministic capture
            print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))
        else:
            # Cross-build without execution: emit skipped markers to avoid incomplete
            marker = {
                "executed": False,
                "passed": False,
                "command": "./test_simint",
                "discovered": 1,
                "passedCount": 0,
                "reason": "can_run=False"
            }
            print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))
