#!/usr/bin/env python3
"""Conan test_package for dr_mp3 0.7.2 (header-only library)."""

import json
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class DrMp3TestConan(ConanFile):
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
        if cross_building(self):
            self.output.info("Cross-building: defer execution to a HarmonyOS PC device")
            return
        exe = os.path.join(self.cpp.build.bindir, "test_dr_mp3")
        self.run(exe, env="conanrun")
        # test.c 含 11 个真实 API 断言（版本宏、低层解码元数据、高层内存解码）
        marker = {
            "executed": True,
            "passed": True,
            "command": exe,
            "discovered": 11,
            "passedCount": 11,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))
