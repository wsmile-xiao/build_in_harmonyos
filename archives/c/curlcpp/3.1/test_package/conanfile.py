#!/usr/bin/env python3
"""Conan test_package — curlcpp 3.1.

Builds test.cpp against the packaged curlcpp (C++11, offline-safe: no
perform() call ever touches the network) and runs it. Evidence markers:

- HMBS_TEST_PACKAGE_RESULT: discovered/passedCount parsed from the real
  "RESULT: P passed, F failed" trailer line of the test binary output.
- HMBS_UPSTREAM_TEST_RESULT: status=no_tests. Upstream registers no
  automated suite (no enable_testing()/add_test(); test/ holds only
  network-dependent example programs; audit in MANIFEST.yml). Re-emitted
  here because the main-recipe build() output may be skipped on cache-hit
  ("Already installed!") preflight rounds.
"""

import json
import os
import re
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class CurlcppTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # curl_easy.h 公开 #include <curl/curl.h>；直连 curl 使 CMakeDeps 为消费者生成完整 CURL 配置（cpr 同款做法）。
        self.requires("curl/8.15.0.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info(
                "cross-building: curlcpp consumer linked but cannot run"
            )
            return
        binary = os.path.join(self.cpp.build.bindirs[0], "test_curlcpp")
        if not os.path.isfile(binary):
            raise ConanException("test binary not found: %s" % binary)
        logfile = os.path.join(self.build_folder, "test_curlcpp.log")
        # Redirect to a log file (c10t precedent): keeps the real output
        # parseable even when the binary exits non-zero, and never depends
        # on self.run() return-value semantics.
        cmd = "%s > %s 2>&1" % (shlex.quote(binary), shlex.quote(logfile))
        self.run(cmd, env="conanrun", ignore_errors=True)

        out = ""
        if os.path.isfile(logfile):
            with open(logfile, "r", encoding="utf-8", errors="replace") as f:
                out = f.read()
        self.output.info("test_curlcpp output:\n" + out)

        match = re.search(r"RESULT: (\d+) passed, (\d+) failed", out)
        if not match:
            raise ConanException(
                "test_curlcpp produced no RESULT line — harness broken"
            )
        passed = int(match.group(1))
        failed = int(match.group(2))
        discovered = passed + failed
        ok = failed == 0 and discovered > 0

        marker = {
            "executed": True,
            "passed": ok,
            "command": "./test_curlcpp",
            "discovered": discovered,
            "passedCount": passed,
        }
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
        )
        if not ok:
            raise ConanException(
                "test_curlcpp failed: {}/{} cases failed".format(failed, discovered)
            )

        upstream_marker = {
            "status": "no_tests",
            "framework": "ctest",
            "command": "ctest --output-on-failure",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "curlcpp 3.1 上游无可接入的自动化测试套件：顶层 CMakeLists.txt "
                "从未调用 enable_testing()/add_test()；test/ 目录仅定义 7 个需外网"
                "访问的示例程序目标，无断言、无测试框架注册，无法通过 ctest "
                "发现或执行（详见 test_package/MANIFEST.yml 审计）"
            ),
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT="
            + json.dumps(upstream_marker, ensure_ascii=False)
        )
        self.output.info("curlcpp consumer test_package passed")
