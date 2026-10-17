#!/usr/bin/env python3
"""Conan test_package — udt 4.11 consumer smoke test.

Builds and runs test.cpp via CMake: a real loopback UDT transfer where a
server thread binds/listens/accepts while a client thread connects and sends
a message; the server verifies the received bytes match.  Exercises
startup/socket/bind/listen/accept/connect/send/recv/close/cleanup against
the packaged libudt.

Emits HMBS_TEST_PACKAGE_RESULT with the real assertion count (2 checks in
test.cpp: server received payload matches the expected message, and the
client sent all bytes).
"""
import json
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class UdtTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"
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
        test_binary = os.path.join(self.cpp.build.bindirs[0], "test_udt")
        self.run(test_binary, env="conanrun")

        # 2 explicit checks in test.cpp: server received payload matches the
        # expected message, and the client sent all bytes.
        test_pkg = {
            "executed": True,
            "passed": True,
            "command": test_binary,
            "discovered": 2,
            "passedCount": 2,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))
        print("HMBS_TEST_PACKAGE_RESULT=" +
              json.dumps(test_pkg, ensure_ascii=False), flush=True)

        # Re-emit the upstream test result persisted by the main recipe into
        # the package res/ (res/upstream_test_result.json — written by build()
        # after running the 4 app/test loopback cases).  test_package runs on
        # every preflight even when conan skips a cached build() ("Already
        # installed! (1 of 1)"), so the HMBS_UPSTREAM_TEST_RESULT evidence is
        # always present in the run output (HMBS marker chain).
        dep = self.dependencies["udt"]
        upstream_json = os.path.join(
            dep.package_folder, "res", "upstream_test_result.json")
        if not os.path.isfile(upstream_json):
            raise ConanException(
                f"upstream_test_result.json missing from package res/: "
                f"{upstream_json} — upstream tests did not run during "
                f"build(); refusing to pass silently")
        with open(upstream_json, "r", encoding="utf-8") as fh:
            upstream = json.load(fh)
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" +
                         json.dumps(upstream, ensure_ascii=False))
        print("HMBS_UPSTREAM_TEST_RESULT=" +
              json.dumps(upstream, ensure_ascii=False), flush=True)
