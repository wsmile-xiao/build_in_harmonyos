#!/usr/bin/env python3
"""Conan test_package for debsig-verify 0.34 (executable).

Runs test.sh which executes the packaged debsig-verify binary and asserts
its real behavior: --version/--help exit 0 with non-empty output, and a
missing input file is rejected with a non-zero exit code.

After test.sh, re-emits HMBS_UPSTREAM_TEST_RESULT from the packaged
res/upstream_test_result.json (persisted by build() after it ran the 21
upstream autotest cases via `make check`). test_package runs on every
preflight even when conan skips a cached build() ("Already installed!"),
so the upstream evidence marker is always present in the run output.
If the packaged JSON is missing the package was produced without running
the upstream suite; that is an explicit failure, never a silent pass.
"""
import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException


class DebsigVerifyTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # 主包 build() 已证实此 worker 沙箱内 profile 默认的
        # /data/service/hnp/bin/bash 不可达（configure[139] Error 127）。
        # 按 E325 逐级探测可达 shell；test.sh 为 POSIX 写法，/bin/sh 可跑。
        shell = None
        for cand in (os.environ.get("SHELL"), os.environ.get("CONFIG_SHELL"),
                     shutil.which("sh"), "/bin/sh", "/system/bin/sh"):
            if cand and os.path.isfile(cand):
                shell = cand
                break
        if shell is None:
            raise ConanException(
                "no accessible POSIX shell found to run test.sh")
        # 本轮真机 TC1 报二进制不在 PATH：先打印诊断（只读），再跑测试。
        try:
            _dep = self.dependencies["debsig-verify"]
            _bindir = os.path.join(_dep.package_folder, "bin")
            self.output.info("test_package diag: package bin listing: {}".format(
                sorted(os.listdir(_bindir)) if os.path.isdir(_bindir)
                else "no bindir {}".format(_bindir)))
        except Exception as _exc:
            self.output.warning("test_package diag failed: {}".format(_exc))
        self.run("{} test.sh".format(shell), env="conanrun")

        # Re-emit the upstream test result marker from the packaged JSON.
        dep = self.dependencies["debsig-verify"]
        result_path = os.path.join(
            dep.package_folder, "res", "upstream_test_result.json")
        if not os.path.isfile(result_path):
            raise ConanException(
                "upstream_test_result.json not found in package ({}): "
                "upstream tests did not run during build(); refusing to "
                "pass silently".format(result_path))
        with open(result_path, "r", encoding="utf-8") as f:
            upstream = json.load(f)
        print("HMBS_UPSTREAM_TEST_RESULT=" +
              json.dumps(upstream, ensure_ascii=False))
