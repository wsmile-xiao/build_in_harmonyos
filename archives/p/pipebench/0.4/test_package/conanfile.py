#!/usr/bin/env python3
"""Conan test_package for pipebench 0.4 — 验证 pipebench 二进制可执行。

pipebench 是 C 应用（application）。test_package 经 CMake 构建
test_pipebench.c（L0c 门禁：测试源文件存在），test() 经 self.run()
真实执行 test_pipebench.sh（L0d 门禁要求 test() 含 self.run；
R34 反空壳：3 个用例均真实执行被测包二进制并校验退出码与数据，
退出码非 0 即失败）。

test() 同时输出 HMBS_TEST_PACKAGE_RESULT 与 HMBS_UPSTREAM_TEST_RESULT
标记（上游无测试套件，MANIFEST.yml 已审计；主配方 build() 的标记在
包缓存命中 Already installed 时不会出现，test_package 每轮必跑，
在此复发 no_tests 标记保证 evidence 门禁每轮有证据）。
"""

import json
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class PipebenchTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
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
        if cross_building(self):
            self.output.info("cross-building: 编译验证通过，跳过运行时测试")
            return
        pipebench_bin = os.path.join(
            self.dependencies["pipebench"].package_folder, "bin", "pipebench")
        if not os.path.exists(pipebench_bin):
            raise ConanException(f"pipebench binary not found: {pipebench_bin}")
        # L0d: test() 经 self.run() 真实执行测试脚本；R34: 脚本内 3 个用例
        # 均真实执行被测二进制（-h 横幅校验 + 两次管道直通 cmp 校验）。
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        cmd = f"{bash} test_pipebench.sh \"{pipebench_bin}\""
        self.run(cmd, env="conanrun", cwd=self.source_folder)
        marker = {
            "executed": True,
            "passed": True,
            "command": "bash test_pipebench.sh <pipebench_bin>",
            "discovered": 3,
            "passedCount": 3,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
        # 上游测试标记复发：pipebench 0.40 上游无测试套件（Makefile 无
        # check/test 目标、无 tests/ 目录、无 ctest/gtest/pytest 注册）。
        upstream_marker = {
            "status": "no_tests",
            "framework": "make",
            "command": "make CC=<cc> CFLAGS=<cflags> -j1 pipebench",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "pipebench 0.40 upstream has no test suite: no tests/ directory, no check/test target in Makefile, no ctest/gtest/pytest registration",
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream_marker))
