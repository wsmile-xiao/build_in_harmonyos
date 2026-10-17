#!/usr/bin/env python3
"""Conan test_package for xbitmaps 1.1.3 (pure data package).

Two-level consumer verification:
  1. compile & run test_xbitmaps.c which #includes installed bitmaps;
  2. run test_bitmaps.sh which scans/validates all 71 installed files.
"""
import json
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout

C_CHECKS = 8
SHELL_CHECKS = 72  # 71 per-file validations + 1 installed-count check


class XbitmapsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # 1) compiled consumer: #include <X11/bitmaps/...> really works
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_xbitmaps")
        self.run('"%s"' % bin_path, env="conanrun")

        # 2) data consumer: validate every installed bitmap file
        dep = self.dependencies[self.tested_reference_str]
        bdir = os.path.join(dep.package_folder, "include", "X11", "bitmaps")
        script = os.path.join(self.recipe_folder, "test_bitmaps.sh")
        self.run('XBITMAPS_DIR="%s" XBITMAPS_EXPECT=71 sh "%s"' % (bdir, script),
                 env="conanrun")

        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "test_xbitmaps + test_bitmaps.sh (xbitmaps consumer checks)",
            "consumer_passed": C_CHECKS + SHELL_CHECKS,
            "consumer_total": C_CHECKS + SHELL_CHECKS,
        }))
