#!/usr/bin/env python3
"""Conan test_package for KWStyle (CLI 消费者视角验证).

KWStyle 是命令行工具而非库，因此「消费者用例」= 模拟业务上层组件把它当工具调用：
  1. `KWStyle -version` 可执行且输出版本串（上游为单横线选项，非 `--version`）
  2. 对「有风格错误」的 C++ 文件跑 `-xml` 规则 → 退出码非 0 且导出 XML 含 <Error>
  3. 对「风格干净」的 C++ 文件跑同一规则 → 退出码 0

断言全部基于上游退出码语义：kwsStyle.cxx 结尾 `if(nerrors > 0) return EXIT_FAILURE;`
（源码 eb1e46d57db0）。测试走 test.sh，因为 OHOS 的 /system/bin/sh (mksh) 不能直接
执行 ELF 二进制，需用 bash 包装（仓库通行做法，见 2048.c / aaphoto）。

验证这三点而非仅 `-version`，是为了满足 R34/R40：消费者测试必须实质调用被测产物
并验证可观测行为，不能只调用 version()。
"""
import os

from conan import ConanFile


class KWStyleTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS /system/bin/sh (mksh) 无法执行 ELF 二进制；用 bash 包装执行。
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
