#!/usr/bin/env python3
"""Conan test_package — runs the packaged config.sub/config.guess scripts on the device."""
import json
import os
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment


class AutotoolsDevTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies[self.tested_reference_str].package_folder
        config_sub = os.path.join(pkg, "share", "misc", "config.sub")
        config_guess = os.path.join(pkg, "share", "misc", "config.guess")
        if not os.path.isfile(config_sub) or not os.path.isfile(config_guess):
            raise RuntimeError("config.sub/config.guess were not packaged")
        test_script = os.path.join(self.recipe_folder, "test.sh")
        # HMBS 平台诊断 [shell_getcwd]：不得硬编码 /data/service/hnp/bin/bash
        # （HNP bash 在 HMFS/HMDFS 上 getcwd 失败）；优先 HMBS 注入的
        # CONFIG_SHELL/SHELL（真机为 /bin/sh）。test.sh 为 POSIX 兼容脚本，
        # /bin/sh 可可靠执行。
        bash = (os.environ.get("CONFIG_SHELL")
                or os.environ.get("SHELL") or "/bin/sh")

        tmpdir = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                  or os.environ.get("TEMP")
                  or os.path.join(self.build_folder, ".tmp"))
        os.makedirs(tmpdir, exist_ok=True)

        # L0d 门禁（ci/conan/build_and_test.sh grep "self\.run"）要求 test()
        # 通过 self.run() 真实执行测试程序，subprocess.run 不算数。输出重定向
        # 到日志文件，随后解析 RESULT 行以输出 HMBS_TEST_PACKAGE_RESULT。
        # Conan 2.x self.run(env=...) 只接受环境脚本文件名列表（["conanrun"]）或
        # None，不接受 VAR=value dict——传 dict 会命中
        # "AssertionError: env argument to ConanFile.run() should be a list"
        # （真机日志 2026-08-22；与 address-standardizer 周期 19、abiword-plugin-
        # openwriter E9 同因同解）。改用 Environment.define + apply() 把变量注入
        # 进程环境，self.run() 的子进程（shell=True）自动继承 os.environ；
        # env=None 明确不 source 任何环境脚本，行为可预期。
        env_vars = Environment()
        env_vars.define("CONFIG_SUB", config_sub)
        env_vars.define("TMPDIR", tmpdir)
        env_vars.define("TMP", tmpdir)
        env_vars.define("TEMP", tmpdir)
        logfile = os.path.join(self.build_folder, "test_package.log")
        cmd = f'"{bash}" "{test_script}" > "{logfile}" 2>&1'
        with env_vars.vars(self).apply():
            self.run(cmd, env=None, ignore_errors=True)

        out = ""
        if os.path.isfile(logfile):
            with open(logfile, "r", encoding="utf-8", errors="replace") as f:
                out = f.read()
        self.output.info(f"test.sh log tail:\n" + "\n".join(out.splitlines()[-12:]))

        # test.sh 内置 3 个断言：OHOS 三元组、GNU/Linux 三元组、幂等性
        m = re.search(r"RESULT: (\d+) passed, (\d+) failed", out)
        passed = int(m.group(1)) if m else 0
        failed = int(m.group(2)) if m else 1
        discovered = passed + failed
        ok = failed == 0 and discovered > 0
        marker = {
            "executed": True,
            "passed": ok,
            "command": f"{bash} {test_script}",
            "discovered": discovered,
            "passedCount": passed,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))
        if not ok:
            raise RuntimeError("test.sh failed")

        # 复发 HMBS_UPSTREAM_TEST_RESULT：build() 的 make check 结果已由 package()
        # 持久化为 <pkg>/res/upstream_test_result.json。test_package 每轮必跑，而
        # conan create 命中包缓存（"Already installed!"）时 build() 会被跳过（第 11
        # 轮真机日志），若只靠 build() 输出标记，缓存命中轮次将缺失上游测试证据。
        # 文件缺失或内容非法则显式失败，不静默通过。
        upstream_json_path = os.path.join(pkg, "res", "upstream_test_result.json")
        if not os.path.isfile(upstream_json_path):
            raise ConanException(
                f"upstream_test_result.json not found in package: {upstream_json_path}")
        with open(upstream_json_path, "r", encoding="utf-8") as f:
            upstream_marker = json.load(f)
        required = ("status", "framework", "command", "discovered",
                    "executed", "passed", "failed", "skipped")
        if (not all(k in upstream_marker for k in required)
                or upstream_marker.get("status") != "passed"
                or upstream_marker.get("discovered", 0) <= 0
                or upstream_marker.get("executed", 0) != upstream_marker.get("discovered")):
            raise ConanException(
                "invalid upstream_test_result.json: "
                + json.dumps(upstream_marker, ensure_ascii=False))
        self.output.info("HMBS_UPSTREAM_TEST_RESULT="
                         + json.dumps(upstream_marker, ensure_ascii=False))
        self.output.info("autotools-dev config.sub functional test passed")
