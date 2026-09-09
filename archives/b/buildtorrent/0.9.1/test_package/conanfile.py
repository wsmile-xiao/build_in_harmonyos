#!/usr/bin/env python3
"""Conan test_package — buildtorrent 0.9.1（torrent 生成命令行工具）。

buildtorrent 是工具型包（bin/buildtorrent），无库可链接，因此 build() 不做
CMake 链接；test() 通过 self.run() 在真机执行 test_buildtorrent.sh，对已安装
二进制做 5 项内容级功能验证（--version、--help、单文件生成、确定性字段复现、
magnet 输出），满足 L0d（test() 含 self.run）与 R34（真实调用被测包产物）。

证据标记：
- HMBS_TEST_PACKAGE_RESULT：discovered/passedCount 取自脚本真实计数
  （RESULT: N passed, M failed 行）。
- HMBS_UPSTREAM_TEST_RESULT：status=no_tests。上游发布包无 tests/ 目录、
  Makefile.am 无 TESTS/check_PROGRAMS 目标（审计见 MANIFEST.yml）。在每轮必跑的
  test() 中复发该标记——主配方 build() 无上游测试输出，包缓存命中轮次也需证据。
"""
import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment


class BuildtorrentTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        from conan.tools.layout import basic_layout
        basic_layout(self)

    def build(self):
        # 工具型包无需链接验证；功能验证在 test() 中对 bin/buildtorrent 执行。
        pass

    def test(self):
        buildtorrent = os.path.join(
            self.dependencies["buildtorrent"].package_folder,
            "bin", "buildtorrent")
        if not os.path.isfile(buildtorrent):
            raise ConanException(
                "buildtorrent binary not found in package: %s" % buildtorrent)

        shell = (os.environ.get("CONFIG_SHELL")
                 or os.environ.get("SHELL") or "/bin/sh")

        tmpdir = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                  or os.environ.get("TEMP")
                  or os.path.join(self.build_folder, ".tmp"))
        os.makedirs(tmpdir, exist_ok=True)

        test_script = os.path.join(self.recipe_folder, "test_buildtorrent.sh")
        logfile = os.path.join(self.build_folder, "test_package.log")

        env_vars = Environment()
        env_vars.define("BUILDTORRENT_BIN", buildtorrent)
        env_vars.define("TMPDIR", tmpdir)
        env_vars.define("TMP", tmpdir)
        env_vars.define("TEMP", tmpdir)

        inner = '"%s" "%s" > "%s" 2>&1' % (shell, test_script, logfile)
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
        self.output.info("test_buildtorrent.sh log:\n"
                         + "\n".join(out.splitlines()[-16:]))

        m = re.search(r"RESULT: (\d+) passed, (\d+) failed", out)
        if not m:
            raise ConanException(
                "test_buildtorrent.sh produced no RESULT line — harness broken")
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
                "test_buildtorrent.sh failed: %d/%d cases failed"
                % (failed, discovered))

        # 上游测试标记：buildtorrent 0.9.1 上游无测试套件。
        # 审计依据（详见 test_package/MANIFEST.yml upstream_test_audit）：
        # 发布 tarball 无 tests/ 目录与 *test* 源文件；Makefile.am 仅有
        # bin_PROGRAMS/man_MANS，无 TESTS/check_PROGRAMS；configure.ac 无测试接线。
        upstream_marker = {
            "status": "no_tests",
            "framework": "autotools",
            "command": "make check (upstream provides no check target)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "buildtorrent 0.9.1 上游发布包无任何测试套件："
                "tarball 顶层 26 文件无 tests/ 或 test/ 目录、无 *test* 源文件；"
                "Makefile.am 仅定义 bin_PROGRAMS=buildtorrent 与 man_MANS，"
                "无 TESTS/check_PROGRAMS；configure.ac 无测试接线；"
                "README/NEWS/ChangeLog/待办清单仅描述构建与用法，无测试入口"),
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT="
                         + json.dumps(upstream_marker, ensure_ascii=False))
        self.output.info("buildtorrent functional test_package passed")
