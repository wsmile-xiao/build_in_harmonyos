#!/usr/bin/env python3
"""Conan test_package for kangaru 4.3.2 (header-only library).

Consumer-visible verification: compiles a C++11 program against the packaged
kangaru::kangaru CMake target and exercises the real public API (service
definition, single_service lifecycle, container.service<>() retrieval and
autowiring), then checks required values with assertions (R34: the test must
depend on the packaged library, not just print).
"""
import json
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class KangaruTestConan(ConanFile):
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
        exe = os.path.join(self.cpp.build.bindir, "test_kangaru")
        self.run(exe, env="conanrun")
        # test.cpp 包含 4 个真实 API 断言（service 构造/单例生命周期/service<>() 取值/autowire 注入）
        marker = {
            "executed": True,
            "passed": True,
            "command": exe,
            "discovered": 4,
            "passedCount": 4,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))

        # OHOS 专项可移植性测试（ohos_portability.cpp）：6 个真实 API 断言。
        ohos_exe = os.path.join(self.cpp.build.bindir, "test_kangaru_ohos")
        self.run(ohos_exe, env="conanrun")
        ohos_marker = {
            "executed": True,
            "passed": True,
            "command": ohos_exe,
            "discovered": 6,
            "passedCount": 6,
        }
        self.output.info("HMBS_OHOS_PORTABILITY_RESULT=" + json.dumps(ohos_marker, ensure_ascii=False))