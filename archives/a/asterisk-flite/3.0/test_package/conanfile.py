#!/usr/bin/env python3
"""Conan test_package — asterisk-flite 3 (Asterisk app_flite.so 模块)。

R34 实质验证：test() 真实执行 check_app_flite.py，对安装产物
lib/asterisk/modules/app_flite.so 做 ELF/符号/flite 静态链接检查；
HMBS_TEST_PACKAGE_RESULT 标记由 checker 在真实断言执行结束后输出。

每轮必跑的 test() 在此复发 HMBS_UPSTREAM_TEST_RESULT(status=no_tests)
上游测试标记：主配方 build() 的标记在包缓存命中（Already installed!）时
不会出现，而 test_package test() 每轮必跑，保证 evidence 门禁每轮都能拿到
上游测试标记。
"""
import json
import os
import sys

from conan import ConanFile
from conan.tools.env import Environment


class AsteriskFliteTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["asterisk-flite"]
        mod = os.path.join(dep.package_folder, "lib", "asterisk",
                           "modules", "app_flite.so")
        assert os.path.isfile(mod), f"app_flite.so not found at {mod}"
        self.output.info(f"app_flite.so found: {mod}")

        checker = os.path.join(self.source_folder, "check_app_flite.py")
        # checker 内部会再拼接 "app_flite.so"，故传目录而非完整路径
        env = Environment()
        env.define("TEST_APP_FLITE_MOD", os.path.dirname(mod))
        with env.vars(self).apply():
            # OHOS：/system/bin/sh (mksh) 不能直接执行 ELF；checker 为纯 Python，
            # 经 sys.executable 运行（与 asterisk-speex test_package 同模式）。
            self.run(f'"{sys.executable}" "{checker}"')

        # 上游测试标记：zaf/Asterisk-Flite v3.0 上游无测试套件（审计详见
        # test_package/MANIFEST.yml 的 upstream_test_audit：Makefile 仅含
        # all/install/samples/clean 目标、无 tests/ 目录、无 CI 测试配置）。
        upstream_marker = {
            "status": "no_tests",
            "framework": "none",
            "command": "make -n (upstream Makefile has no check/test target)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": ("asterisk-flite 3 上游无测试套件：源码仅 app_flite.c + "
                       "Makefile + flite.conf.sample，Makefile 无 check/TESTS "
                       "目标，仓库无 tests/ 目录与测试框架配置"),
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" +
                         json.dumps(upstream_marker, ensure_ascii=False))
