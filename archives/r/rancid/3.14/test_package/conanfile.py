#!/usr/bin/env python3
"""Conan test_package — rancid 3.14 消费者冒烟测试。

rancid 是自包含 prefix 的 CLI/脚本工具集（bin/ C 助手 + perl 脚本、lib/rancid/
perl 模块），没有可链接的库 API，因此消费者用例按"真实调用方式"验证打包产物：

  (A) hpuifilter（无参数）→ 用法 + 退出码 64 (EX_USAGE)
  (B) par（-h）           → 退出码 64 (EX_USAGE)
  (C) rancid.pm 已安装且 perl -c 语法有效
  (D) use rancid 模块可加载（perl 脚本的模块依赖在包内齐全）
  (E) bin/rancid 脚本已安装且 perl -c 语法有效

test.sh 自身维护确定性计数器（RANCID_TEST_TOTAL/PASS/FAIL），本 conanfile
从 test.sh 实际运行输出解析这些计数来生成 HMBS 标记 —— 数字唯一来源为真机
上 test.sh 的真实执行，不做任何算术修补或回退猜测。
"""
import json
import os
import re

from conan import ConanFile


class RancidTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["rancid"].package_folder
        # 在 conan test_package 中 self.recipe_folder 即本 test_package 目录
        test_sh = os.path.join(self.recipe_folder, "test.sh")
        log = os.path.join(self.build_folder, "rancid_test.log")
        # OHOS /system/bin/sh (mksh) 不能直接执行 ELF 二进制，用 bash 包装。
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        cmd = f'"{bash}" "{test_sh}" "{pkg}"'
        # 输出重定向到 log，既留痕又供解析
        self.run(f'{cmd} > "{log}" 2>&1', env="conanrun")
        out = ""
        if os.path.isfile(log):
            with open(log, encoding="utf-8", errors="replace") as f:
                out = f.read()
        self.output.info("=== rancid test_package (tail) ===")
        for line in (out.splitlines() or [])[-20:]:
            self.output.info(line)
        # 从 test.sh 真实输出解析确定性计数（唯一来源）
        def _int(name):
            m = re.search(rf"^{name}=(\d+)", out, flags=re.MULTILINE)
            return int(m.group(1)) if m else -1

        total = _int("RANCID_TEST_TOTAL")
        passed = _int("RANCID_TEST_PASS")
        failed = _int("RANCID_TEST_FAIL")
        # 正确性断言：数字只能来自日志；缺失/非法 → 如实失败
        self.output.info(f"parsed counts: total={total} passed={passed} failed={failed}")
        all_ok = total > 0 and passed + failed == total and failed == 0 and passed == total
        test_result = {
            "executed": True,
            "passed": all_ok,
            "command": cmd,
            "discovered": total,
            "passedCount": passed,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_result, ensure_ascii=False))
        # 上游无测试 → no_tests（审计见 test_package/MANIFEST.yml upstream_test_audit）
        audit_cmd = ("grep -rnE '(^|[^A-Za-z_])TESTS|check_PROGRAMS|"
                     "check-local|check_SCRIPTS' */Makefile.am configure.ac")
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "no_tests",
            "framework": "none",
            "command": audit_cmd,
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "upstream rancid 3.14 release tarball contains no automated "
                "tests: no TESTS/check_PROGRAMS/check-local target in any "
                "Makefile.am, configure.ac has no test macros, and no "
                "t/ tests/ test/ directory or *.t file exists (audit in "
                "test_package/MANIFEST.yml upstream_test_audit)"
            ),
        }, ensure_ascii=False))
        if not all_ok:
            raise RuntimeError(
                f"rancid consumer test failed: total={total} passed={passed} "
                f"failed={failed} (from {log})"
            )
