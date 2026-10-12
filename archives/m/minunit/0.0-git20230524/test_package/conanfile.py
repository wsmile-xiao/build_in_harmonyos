#!/usr/bin/env python3
"""Test package for minunit 0.0-git20230524 (single-header C unit test framework)"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class MinunitTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # R32：OHOS 下 SDK clang 以 Linux 语义配置（daw-utf-range 2.2.6 先例）
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning("cross-building: skip runtime test")
            return
        exe = os.path.join(self.cpp.build.bindirs[0], "test_minunit")
        out_file = os.path.join(self.build_folder, "test_minunit_output.txt")
        # minunit 契约：MU_EXIT_CODE = 失败计数。本测试含 5 个故意失败用例
        # （校验断言捕获能力）→ 期望退出码 5；ignore_errors 取回退出码后
        # 连同 MU_REPORT 输出精确校验。
        with open(out_file, "w") as f:
            retcode = self.run('"%s"' % exe, stdout=f, env="conanrun", ignore_errors=True)
        with open(out_file) as f:
            out = f.read()
        self.output.info("──── test_minunit output ────\n%s────────────────────────────" % out)
        if retcode != 5:
            raise ConanException(
                "test_minunit FAILED: minunit contract expects MU_EXIT_CODE==5 "
                "(5 designed-to-fail cases), got %d" % retcode
            )
        for expected in ("10 tests, 10 assertions, 5 failures",
                         "setup_calls=10 teardown_calls=10"):
            if expected not in out:
                raise ConanException(
                    "test_minunit FAILED: expected %r in output, got:\n%s" % (expected, out)
                )
        self.output.info(
            "test_minunit PASS: 10 tests / 10 assertions / 5 designed failures "
            "exactly as expected (exit code 5), setup/teardown hooks fired per test"
        )
