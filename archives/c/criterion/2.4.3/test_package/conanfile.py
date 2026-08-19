#!/usr/bin/env python3
"""Conan test_package for criterion 2.4.3 — Conan L1 official test.

Uses CMake to build the test (CMakeLists.txt already exists).
CMakeToolchain handles compiler settings automatically (R33 compliant).
CI runs this automatically via `conan create` (which invokes test_package).

test() 输出两个 HMBS 机器证据标记：
- HMBS_TEST_PACKAGE_RESULT: 冒烟测试 (./test_criterion) 的真实用例计数，
  从 criterion 的 Synthesis 汇总行解析（Tested/Passing），非写死。
- HMBS_UPSTREAM_TEST_RESULT: 复发 build() 中 meson test 的结果 JSON
  （持久化于 <package>/res/upstream_test_result.json，包缓存命中时
  build() 不重跑，仅 test_package 每轮必跑，保证标记每轮出现）。
  文件缺失或 status != passed 时抛 ConanException 显式失败，不静默通过。
"""
import json
import os
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout


class CriterionTestConan(ConanFile):
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
        # criterion 的 meson.build 用 both_libraries() 同时构建 shared+static，
        # CMakeDeps 优先选 shared (libcriterion.so.3)，测试二进制动态链接它。
        # OHOS 上 conanrun 环境不会正确设置 LD_LIBRARY_PATH（musl 动态链接器
        # 不支持 $ORIGIN RPATH，conanrun 的 LD_LIBRARY_PATH 在 OHOS 上未生效），
        # 导致运行时报 "Error loading shared library libcriterion.so.3"。
        # 手动将 LD_LIBRARY_PATH 指向 conan 包的 lib 目录（与 minizip/avfs 等
        # 包的处理方式一致），不依赖 conanrun。
        dep = self.dependencies["criterion"]
        libdir = os.path.join(dep.package_folder, dep.cpp_info.libdirs[0])
        os.environ["LD_LIBRARY_PATH"] = libdir + ":" + os.environ.get("LD_LIBRARY_PATH", "")

        # 1) 冒烟测试：经 self.run()（Conan 官方运行器，满足 CI L0d 门禁要求）
        #    真机执行 ./test_criterion，输出重定向到日志文件后回读，
        #    从 criterion Synthesis 汇总行解析真实计数
        #    （Tested: N | Passing: M），据此输出 HMBS_TEST_PACKAGE_RESULT。
        log = os.path.join(self.build_folder, "test_criterion.log")
        rc = self.run("./test_criterion > '%s' 2>&1" % log,
                      cwd=self.build_folder, ignore_errors=True)
        with open(log, encoding="utf-8", errors="replace") as f:
            out = f.read()
        print(out, end="" if out.endswith("\n") else "\n")
        m = re.search(r"Tested:\s*(\d+)\s*\|\s*Passing:\s*(\d+)", out)
        discovered = int(m.group(1)) if m else 0
        passed_count = int(m.group(2)) if m else 0
        tp_ok = (rc == 0 and discovered > 0
                 and passed_count == discovered)
        tp_result = {
            "executed": True,
            "passed": tp_ok,
            "command": "./test_criterion",
            "discovered": discovered,
            "passedCount": passed_count,
        }
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(tp_result), flush=True)
        if not tp_ok:
            raise ConanException(
                "[criterion] test_package smoke test failed: %s"
                % json.dumps(tp_result))

        # 2) 复发上游测试结果（build() 已执行 meson test 并持久化进包）。
        jf = os.path.join(dep.package_folder, "res", "upstream_test_result.json")
        if not os.path.isfile(jf):
            raise ConanException(
                "[criterion] upstream_test_result.json missing from package; "
                "upstream tests did not run in build()")
        with open(jf, encoding="utf-8") as f:
            up_result = json.load(f)
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(up_result), flush=True)
        if up_result.get("status") != "passed":
            raise ConanException(
                "[criterion] upstream tests not passed: %s"
                % json.dumps(up_result))
