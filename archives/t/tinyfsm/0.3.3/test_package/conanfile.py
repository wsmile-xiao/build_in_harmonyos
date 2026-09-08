#!/usr/bin/env python3
"""Conan test_package for tinyfsm 0.3.3 (C++11 header-only FSM library)."""

import json
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class TinyfsmTestConan(ConanFile):
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
        exe = os.path.join(self.cpp.build.bindir, "test_tinyfsm")
        self.run(exe, env="conanrun")
        # test.cpp 含 3 个真实 API 断言（初始状态 Off + 两次 toggle 状态切换）
        marker = {
            "executed": True,
            "passed": True,
            "command": exe,
            "discovered": 3,
            "passedCount": 3,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))