#!/usr/bin/env python3
"""Conan test_package for pcapplusplus 26.07 — consumer view of the public C++ API.

Builds and runs `test_pcapplusplus`, which exercises the installed headers and
libraries through the consumer-facing API only: address parsing, packet crafting,
serialization + re-parse, offline BPF filtering through libpcap, and a pcap file
write/read round-trip. The program prints its own assertion count, reported
through HMBS_TEST_PACKAGE_RESULT. The upstream test summary is re-emitted from
package_folder/res so the CI gate still sees it on Conan cache hits, where
build() is skipped.
"""
import json
import os
import re
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout


class PcapplusplusTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def configure(self):
        # The OHOS profile defines os.version, which this test_package does not use.
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
        # Re-emit the upstream summary captured during build(). On a cache hit
        # build() is skipped, so package_folder/res is the authoritative copy.
        upstream = self._read(os.path.join(self.package_folder, "res",
                                           "upstream_test_result.json"))
        if upstream:
            self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + upstream.strip())

        # Deliberately no can_run() gate: this environment pins
        # tools.build.cross_building:can_run=False, so a gate would silently skip
        # the consumer program and report a false green.
        result = {
            "executed": False,
            "passed": False,
            "command": "./test_pcapplusplus",
            "discovered": 0,
            "passedCount": 0,
        }
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        log_path = os.path.join(self.build_folder, "test_pcapplusplus.log")
        try:
            self.run(f"{bash} -c {shlex.quote('./test_pcapplusplus > ' + shlex.quote(log_path) + ' 2>&1')}",
                     env="conanrun")
            result["executed"] = True
        except Exception as exc:  # noqa: BLE001 - report and fail below
            self.output.error("consumer program did not run: %s" % exc)
        output = self._read(log_path)
        self.output.info(output)
        checks = re.search(r"(\d+)/(\d+) checks passed", output)
        if checks:
            result["passedCount"] = int(checks.group(1))
            result["discovered"] = int(checks.group(2))
        ok = (result["executed"] and result["discovered"] > 0
              and result["passedCount"] == result["discovered"])
        result["passed"] = ok
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(result, ensure_ascii=False))
        if not ok:
            raise ConanException("consumer test failed:\n" + output[-2000:])
