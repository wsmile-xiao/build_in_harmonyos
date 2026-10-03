#!/usr/bin/env python3
"""Conan test_package — tor 0.4.9.11.

settings 声明 os/compiler/build_type/arch 四项（L0p 门禁要求，与主配方同步）。
test() 运行 test.sh（4 个离线用例：--version / --verify-config /
--list-torrc-options / --hash-password，均不触网），解析用例输出并打印
HMBS_TEST_PACKAGE_RESULT 标记（discovered/passedCount 来自真实用例计数），
最后复发包内 res/upstream_test_result.json 的 HMBS_UPSTREAM_TEST_RESULT 标记。
"""
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
import json
import os


class TorTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        bash = os.environ.get("CONFIG_SHELL", "bash")
        log = os.path.join(self.build_folder, "test_package.log")
        cmd = f"cd {self.build_folder} && {bash} test.sh > {log} 2>&1"
        rc = self.run(cmd, env="conanrun", ignore_errors=True)
        discovered = 0
        passed_count = 0
        with open(log, encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if line.startswith("case ") and line.endswith(": PASS"):
                    discovered += 1
                    passed_count += 1
                elif line.startswith("case ") and line.endswith(": FAIL"):
                    discovered += 1
                elif line.startswith("RESULT: "):
                    parts = line[len("RESULT: "):].split("/")
                    if len(parts) == 2:
                        try:
                            passed_count = int(parts[0])
                            discovered = int(parts[1])
                        except ValueError:
                            pass
        ok = (rc == 0) and (discovered > 0) and (passed_count == discovered)
        result = {
            "executed": True,
            "passed": ok,
            "command": cmd,
            "discovered": discovered,
            "passedCount": passed_count,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(result))
        if not ok:
            raise Exception(
                f"test_package 失败: rc={rc} passed={passed_count}/{discovered}"
                f"，详见 {log}")
        # 复发上游测试证据：读取 build() 持久化进包 res/ 的 upstream_test_result.json
        # （torsocks 2.5.0 / git-who/1.3 已验证先例）。真机证据门禁只采集
        # test_package 阶段的标记，文件缺失或非法则显式失败，不静默通过。
        upstream_path = os.path.join(
            self.dependencies["tor"].package_folder,
            "res", "upstream_test_result.json")
        if not os.path.isfile(upstream_path):
            raise ConanException(
                f"包内上游测试结果缺失: {upstream_path}（build() 未持久化）")
        with open(upstream_path, encoding="utf-8") as f:
            upstream_result = json.load(f)
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream_result))
