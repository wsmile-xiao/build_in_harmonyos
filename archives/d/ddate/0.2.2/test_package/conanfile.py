#!/usr/bin/env python3
"""Conan test_package — ddate 0.2.2（Discordian 日期转换命令行工具）。

ddate 是工具型包（bin/ddate），无库可链接，因此 build() 不做 CMake 链接；
test() 通过 self.run() 在真机执行 test_ddate.sh，对已安装二进制做 6 项
内容级功能验证（无参当前日期、指定日期转换、%Y/%B 格式化、非法日期拒绝、
错误参数用法提示），满足 L0d（test() 含 self.run）与 R34（真实调用被测包产物）。

证据标记：
- HMBS_TEST_PACKAGE_RESULT：discovered/passedCount 取自脚本真实计数
  （RESULT: N passed, M failed 行）。
- HMBS_UPSTREAM_TEST_RESULT：status=no_tests。上游发布包无 tests/ 目录、
  CMakeLists 无 enable_testing/add_test（审计见 MANIFEST.yml）。在每轮必跑的
  test() 中复发该标记——主配方 build() 无上游测试输出，包缓存命中轮次也需证据。
"""
import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment


class DdateTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        from conan.tools.layout import basic_layout
        basic_layout(self)

    def build(self):
        # 工具型包无需链接验证；功能验证在 test() 中对 bin/ddate 执行。
        pass

    def test(self):
        ddate = os.path.join(
            self.dependencies["ddate"].package_folder,
            "bin", "ddate")
        if not os.path.isfile(ddate):
            raise ConanException(
                "ddate binary not found in package: %s" % ddate)

        shell = (os.environ.get("CONFIG_SHELL")
                 or os.environ.get("SHELL") or "/bin/sh")

        tmpdir = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                  or os.environ.get("TEMP")
                  or os.path.join(self.build_folder, ".tmp"))
        os.makedirs(tmpdir, exist_ok=True)

        test_script = os.path.join(self.recipe_folder, "test_ddate.sh")
        logfile = os.path.join(self.build_folder, "test_package.log")

        env_vars = Environment()
        env_vars.define("DDATE_BIN", ddate)
        env_vars.define("TMPDIR", tmpdir)
        env_vars.define("TMP", tmpdir)
        env_vars.define("TEMP", tmpdir)

        inner = '"%s" "%s" "%s" > "%s" 2>&1' % (shell, test_script, ddate, logfile)
        if shutil.which("timeout"):
            cmd = "timeout 90 %s" % inner
        elif os.path.isfile("/data/service/hnp/bin/timeout"):
            cmd = "/data/service/hnp/bin/timeout 90 %s" % inner
        else:
            cmd = inner
        with env_vars.vars(self).apply():
            self.run(cmd, env=None, ignore_errors=True)

        out = ""
        if os.path.isfile(logfile):
            with open(logfile, "r", encoding="utf-8", errors="replace") as f:
                out = f.read()
        self.output.info("test_ddate.sh log:\n"
                         + "\n".join(out.splitlines()[-20:]))

        m = re.search(r"RESULT: (\d+) passed, (\d+) failed", out)
        if not m:
            raise ConanException(
                "test_ddate.sh produced no RESULT line — harness broken")
        passed = int(m.group(1))
        failed = int(m.group(2))
        discovered = passed + failed
        ok = failed == 0 and discovered > 0

        marker = {
            "executed": True,
            "passed": ok,
            "command": "%s %s" % (shell, test_script),
            "discovered": discovered,
            "passedCount": passed,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT="
                         + json.dumps(marker, ensure_ascii=False))
        if not ok:
            raise RuntimeError(
                "test_ddate.sh failed: %d/%d cases failed"
                % (failed, discovered))

        # 上游测试标记：ddate 0.2.2 上游无测试套件。
        # 审计依据（详见 test_package/MANIFEST.yml upstream_test_audit）：
        # 发布 tarball 顶层仅 5 个文件（CMakeLists.txt/ddate.c/ddate.1/
        # README.org/.gitignore），无 tests/ 或 test/ 目录、无 *test* 源文件；
        # CMakeLists.txt 无 enable_testing/add_test，仅定义 binary + manpage。
        upstream_marker = {
            "status": "no_tests",
            "framework": "ctest",
            "command": "ctest (upstream provides no tests)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "ddate 0.2.2 上游发布包无任何测试套件："
                "tarball 顶层仅 5 个文件，无 tests/ 或 test/ 目录、"
                "无 *test* 源文件；CMakeLists.txt 仅定义 add_executable(ddate) "
                "与 manpage 压缩目标，无 enable_testing/add_test；"
                "README.org 仅描述构建与历法，无测试入口"),
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT="
                         + json.dumps(upstream_marker, ensure_ascii=False))
        self.output.info("ddate functional test_package passed")
