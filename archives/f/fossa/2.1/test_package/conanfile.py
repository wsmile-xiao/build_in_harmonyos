#!/usr/bin/env python3
"""Conan test_package for fossa 2.1.

Builds and runs test.c against the packaged static library, then reports the
consumer-side result through the HMBS evidence marker. Numbers come from the
test binary's own runtime counters, not from constants in this file.
"""
import json
import os
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.files import load

_RESULT_RE = re.compile(r"assertions=(\d+) failures=(\d+)")


class FossaTestConan(ConanFile):
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
        exe = os.path.join(self.cpp.build.bindirs[0], "test_fossa")
        result_file = os.path.join(self.build_folder, "test_package_result.txt")
        self.run(f"{exe} {result_file}", env="conanrun")

        # 断言数只能来自测试程序自己的运行时计数：取不到就报错，
        # 退化成 0/0 会把「没测到」误报成「全部通过」。
        if not os.path.isfile(result_file):
            raise ConanException(f"test_package 未产出结果文件: {result_file}")
        match = _RESULT_RE.search(load(self, result_file))
        if not match:
            raise ConanException(f"test_package 结果无法解析: {result_file}")
        assertions, failures = int(match.group(1)), int(match.group(2))
        marker = {
            "executed": True,
            "passed": failures == 0,
            "assertions": assertions,
            "failed": failures,
            "command": f"{exe} {result_file}",
        }
        print(f"HMBS_TEST_PACKAGE_RESULT={json.dumps(marker)}", flush=True)
