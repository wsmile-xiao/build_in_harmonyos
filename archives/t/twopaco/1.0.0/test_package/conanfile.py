#!/usr/bin/env python3
"""Conan test_package — twopaco 1.0.0 消费者验证。

twopaco 是纯命令行工具包（无库无头），test() 直接调用被测包产物：
  1. twopaco --help：真实执行 TCLAP 帮助路径，断言退出码 0 且输出非空
  2. graphdump --help：同上
  3. twopaco 端到端：在临时 FASTA（2 条 200bp 确定性序列）上真实建图，
     断言 de_bruijn.bin 存在且非空（空文件比空文件式假阳性在这里会被抓：
     若二进制是 exit-1 桩或静默跳过，本步直接失败）
  4. graphdump -f seq：把上一步产物转文本，断言输出非空且每行 3 列
     （chr pos id），行数 > 0

断言脚本 test_twopaco.py 自行统计 discovered/passedCount 并输出
HMBS_TEST_PACKAGE_RESULT；同时从包内 res/hmbs_upstream.json 重发
HMBS_UPSTREAM_TEST_RESULT（缓存命中轮主 build 跳过时门禁仍需该标记）。
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class TwopacoTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("cross-building：只验编译+链接")
            return
        pkg = self.dependencies[self.tested_reference_str.split("/")[0]].package_folder
        script = os.path.join(self.source_folder, "test_twopaco.py")
        if not os.path.isfile(script):
            raise ConanException("test script missing: " + script)
        self.run('python3 "%s" "%s"' % (script, pkg), env="conanrun")
        self._reemit_upstream()

    def _reemit_upstream(self):
        try:
            dep = self.dependencies[self.tested_reference_str.split("/")[0]]
            cand = os.path.join(dep.package_folder, "res", "hmbs_upstream.json")
            if os.path.isfile(cand):
                with open(cand, "r", encoding="utf-8") as handle:
                    up = json.load(handle)
                marker = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(up, ensure_ascii=False)
                print(marker, flush=True)
                self.output.info(marker)
            else:
                self.output.warning(
                    "hmbs_upstream.json absent from package res/; "
                    "upstream marker left to the main build (cache-miss rounds)")
        except Exception as exc:
            self.output.warning("upstream re-emit failed: %s" % exc)
