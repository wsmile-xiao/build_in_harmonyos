#!/usr/bin/env python3
"""Conan consumer test for libdetourtilecache/1.6.0."""

import json
import os
import re
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class LibdetourtilecacheTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        toolchain = CMakeToolchain(self)
        if str(self.settings.os) == "OHOS":
            toolchain.variables["CMAKE_SYSTEM_NAME"] = "OHOS"
            toolchain.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        toolchain.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            raise ConanException("test_package requires a runnable host")

        test_bin = None
        for root, _, files in os.walk(self.build_folder):
            for filename in files:
                if filename in ("libdetourtilecache_test", "libdetourtilecache_test.exe"):
                    test_bin = os.path.join(root, filename)
                    break
            if test_bin:
                break
        if test_bin is None or not os.path.isfile(test_bin):
            raise ConanException("libdetourtilecache_test binary not found")

        self.run(test_bin, env="conanrun")
        proc = subprocess.run([test_bin], capture_output=True, text=True, timeout=60)
        output = (proc.stdout or "") + (proc.stderr or "")
        self.output.info("consumer test output:\n" + output)
        passed_count = len(re.findall(r"^CHECK-OK:", output, re.MULTILINE))
        expected = 3 if str(self.settings.os) == "OHOS" else 2
        marker = {
            "executed": True,
            "passed": proc.returncode == 0 and passed_count == expected,
            "command": "./libdetourtilecache_test",
            "discovered": expected,
            "passedCount": passed_count,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))
        if not marker["passed"]:
            raise ConanException("test_package failed: %d/%d checks passed" % (passed_count, expected))
