#!/usr/bin/env python3
"""Conan test_package — meojson 5.1.2.

Consumer test: builds a C++17 program that exercises the real meojson public
API (json::parse / json::value accessors / json::array / json::object /
serialization), then runs it. Each assertion fails the process (return 1) if
the API does not behave as expected — this is not an include-only stub.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout


class MeojsonTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

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
            bindirs = self.cpp.build.bindirs
            if not bindirs:
                raise Exception("No bindirs found")
            bin_path = os.path.join(bindirs[0], "test_meojson")
            if not os.path.isfile(bin_path):
                raise Exception(f"Test binary not found: {bin_path}")
            # W4 审计修复（R9）：禁止把 exec 失败静默降级为告警式跳过——那会
            # 形成"测试未运行却报 PASS"的软通过路径。默认任何运行失败都向上
            # 传播使 conan create 失败；仅在显式设置 OHC_ALLOW_TEST_EXEC_SKIP=1
            # 时（用于确凿的 CI 沙箱无法 exec 的极端场景）才跳过并在日志明确
            # 标注 SKIP 而非 PASS。
            skip_ok = os.environ.get("OHC_ALLOW_TEST_EXEC_SKIP") == "1"
            try:
                self.run(bin_path, env="conanrun")
            except ConanException as e:
                if skip_ok and ("Operation not permitted" in str(e) or "Error 126" in str(e)):
                    self.output.warning(
                        f"SKIP: CI sandbox forbids exec ({e}); "
                        "TEST NOT RUN — not counted as pass"
                    )
                else:
                    raise