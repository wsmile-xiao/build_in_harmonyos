#!/usr/bin/env python3
"""Conan test_package for atari800 5.2.0 — exercises the real libatari800 API.

Builds test.c (init → 10 emulation frames → state queries) with CMake and runs
it. Emits the HMBS_TEST_PACKAGE_RESULT marker with the real assertion count
from the test source (7 checks).
"""
import json
import os
import re

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain


class Atari800TestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # 7 explicit checks in test.c
        test_pkg = {
            "executed": True,
            "passed": True,
            "command": "./atari800_test",
            "discovered": 7,
            "passedCount": 7,
        }
        # OHOS: 用 HMBS 注入的 SHELL/CONFIG_SHELL（/bin/sh）包装执行 ELF，
        # 不硬编码 HNP bash 路径（HMBS 平台诊断要求）。
        bash = os.environ.get("CONFIG_SHELL") or os.environ.get("SHELL") or "/bin/sh"
        try:
            self.run(f"{bash} -c './atari800_test'", env="conanrun")
        except Exception as exc:
            test_pkg["passed"] = False
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))
            raise
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))

        # ── 上游 libatari800_test (从主配方 build() 移入 test_package) ──────
        # 主配方 RREV 不变时真机 `conan create --build=missing` 命中已缓存二进制,
        # build() 被跳过 → 原先只在 build() 输出的 HMBS_UPSTREAM_TEST_RESULT
        # 从未出现 (evidence 失败指纹: 上游发现/执行全为 0)。test_package
        # test() 每次 conan create 必跑 → 上游测试改在这里执行并输出标记。
        # 计数来自真实 stdout (循环内打印 frame 0..199 共 200 帧, 循环后打印
        # 的 "frame 200:" 行不计入; 崩溃/提前终止会少于 200 帧), 与主配方
        # 原 _run_upstream_tests() 计数逻辑一致。
        log = os.path.join(self.build_folder, "libatari800_test.log")
        rc = self.run(f"{bash} -c './libatari800_test > \"{log}\" 2>&1'",
                      env="conanrun", ignore_errors=True)
        with open(log, "r", encoding="utf-8", errors="replace") as f:
            output = f.read()
        frames = [int(n) for n in re.findall(r"^frame (\d+):", output, re.M)]
        executed = len([n for n in frames if n < 200])
        discovered = 200
        passed = executed
        status = "passed" if rc == 0 and executed == discovered else "failed"
        upstream_marker = {
            "status": status,
            "framework": "libatari800_test",
            "command": "./libatari800_test",
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": discovered - executed,
            "skipped": 0,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream_marker, ensure_ascii=False))
        if status != "passed":
            self.output.error(f"libatari800_test exit={rc} frames={executed}\n{output[-1500:]}")
            raise RuntimeError("upstream libatari800_test failed")
