#!/usr/bin/env python3
"""Conan test_package for metahtml 5.091 —— 消费者视角真跑包内工具（explicit 驱动）。

断言面（R34 实质依赖被测包）：
  1. 包内 mhc 二进制经 conanrun 环境可加载执行（gdbm/termcap 动态依赖齐全）；
  2. 真渲染语料同构模板，输出与期望逐字节(cmp)+逐行(grep)断言一致；
     期望值设备实测取得（2026-09-27）：<add 40 2> => 42、<and 1 1> => 1。
断言与通过/失败计数在 test.sh 实现（L0c 白名单扩展名 .sh），失败退出码非 0。
"""
import os
import shlex

from conan import ConanFile


class MetahtmlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        test_sh = os.path.join(self.source_folder, "test.sh")
        # cwd 取测试构建目录：测试落盘的 scratch 件留在构建区，不污染源树
        self.run("sh " + shlex.quote(test_sh), cwd=self.build_folder, env="conanrun")
