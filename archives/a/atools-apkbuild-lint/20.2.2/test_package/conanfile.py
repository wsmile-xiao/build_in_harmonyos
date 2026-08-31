#!/usr/bin/env python3
"""Conan test_package — atools-apkbuild-lint 20.2.2（可执行脚本消费者测试）.

运行 test.sh，对安装后的 apkbuild-lint 脚本做真实功能验证：
存在且可执行、干净 APKBUILD 零告警、违规 APKBUILD 输出 [ALxx] 标签并以
非零码退出。test.sh 结束后输出 HMBS_TEST_PACKAGE_RESULT 标记。

随后从包内 res/upstream_test_result.json 复发 HMBS_UPSTREAM_TEST_RESULT：
conan create 缓存命中跳过 build() 时上游证据仍每轮可见；JSON 缺失说明包是
在没有运行上游套件的情况下产出的 —— 显式失败，绝不静默通过。
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanException


class AtoolsApkbuildLintTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS：test.sh 为 POSIX sh；解释器按 CONFIG_SHELL -> /bin/sh 解析
        # （OHOS 的 /bin/sh 即 mksh；不再按名字找 bash——真机上那往往是 mksh/
        # toybox 别名，且本脚本不需要任何 bash 特性）
        sh = os.environ.get("CONFIG_SHELL", "")
        if not sh or not os.path.isfile(sh):
            sh = "/bin/sh"
        self.run("{} test.sh".format(sh), env="conanrun")

        dep = self.dependencies["atools-apkbuild-lint"]
        result_path = os.path.join(
            dep.package_folder, "res", "upstream_test_result.json")
        if not os.path.isfile(result_path):
            raise ConanException(
                "upstream_test_result.json not found in package ({}) — "
                "upstream bats suites did not run during build(); refusing "
                "to pass silently".format(result_path))
        with open(result_path, "r", encoding="utf-8") as f:
            upstream = json.load(f)
        print("HMBS_UPSTREAM_TEST_RESULT=" +
              json.dumps(upstream, ensure_ascii=False))

        files_path = os.path.join(
            dep.package_folder, "res", "upstream_test_files.json")
        if not os.path.isfile(files_path):
            raise ConanException(
                "upstream_test_files.json not found in package ({}) — "
                "per-suite upstream evidence missing".format(files_path))
        with open(files_path, "r", encoding="utf-8") as f:
            files = json.load(f)
        print("HMBS_UPSTREAM_TEST_FILES=" +
              json.dumps(files, ensure_ascii=False))
