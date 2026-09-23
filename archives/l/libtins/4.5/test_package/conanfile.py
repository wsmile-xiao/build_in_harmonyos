#!/usr/bin/env python3
"""Conan test_package for libtins 4.5 — consumer test of the public C++ API.

Builds and runs test_libtins.cpp: crafts Ethernet/IPv4/TCP and Ethernet/IPv4/UDP
PDU trees with the library's public API, serializes them, re-parses the wire
bytes and asserts the decoded fields. The consumer program prints its own
assertion count, which is reported through HMBS_TEST_PACKAGE_RESULT.
"""
import json
import os
import re
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LibtinsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def configure(self):
        # The OHOS profile defines os.version, which this test_package does not use
        self.settings.rm_safe("os.version")

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _read(self, path):
        if not os.path.isfile(path):
            return ""
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return handle.read()

    def test(self):
        test_pkg = {
            "executed": False,
            "passed": False,
            "command": "./test_libtins",
            "discovered": 0,
            "passedCount": 0,
        }
        if not can_run(self):
            # cross-build: compile+link validation only
            test_pkg["command"] = "CMake build (compile+link) only: cannot run on build host"
            test_pkg["passed"] = False
            test_pkg["skipped"] = "cannot run on build host (cross-build)"
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))
            return
        # OHOS: /system/bin/sh cannot load dynamically linked binaries, so run the
        # consumer program through CONFIG_SHELL; tee the output for the report.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        out_file = os.path.join(os.getcwd(), "test_libtins-console.log")
        passed = True
        try:
            self.run(f"{bash} -c {shlex.quote('./test_libtins > ' + shlex.quote(out_file) + ' 2>&1')}",
                     env="conanrun")
        except Exception:
            passed = False
        output = self._read(out_file)
        self.output.info(output)
        checks = re.search(r"test_libtins: (\d+) checks passed", output)
        if checks:
            test_pkg["discovered"] = int(checks.group(1))
        test_pkg["executed"] = True
        test_pkg["passed"] = passed
        test_pkg["passedCount"] = test_pkg["discovered"] if passed else 0
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))
        if not passed:
            raise ConanException("consumer test failed:\n" + output[-2000:])
