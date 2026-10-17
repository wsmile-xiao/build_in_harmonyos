#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conan test_package for rs —— 消费者视角功能测试（测试体系第 2 层）。

rs 是命令行工具（没有库 API 可链接），所以"消费者"就是**装上之后调用它的用户**：
本测试从被测包的 bindir 取出 rs 可执行文件，用真实 stdin/argv 跑七组行为断言
（见 test_rs_consumer.py）。退出码由断言结果决定，因此把包目录改名后这里必然
失败（L1e 破坏性反向验证成立），不是"文件存在就算过"。
"""
import os
import sys

from conan import ConanFile


class RsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        bindirs = dep.cpp_info.bindirs or ["bin"]
        executable = None
        for bindir in bindirs:
            candidate = os.path.join(dep.package_folder, bindir, "rs")
            if os.path.isfile(candidate):
                executable = candidate
                break
        if executable is None:
            self.output.error("rs binary not found under %s (bindirs=%s)"
                              % (dep.package_folder, bindirs))
            raise Exception("installed rs executable is missing")
        script = os.path.join(self.recipe_folder, "test_rs_consumer.py")
        # N_consumer = 1 个消费者程序，内含 7 组行为断言
        self.run('"%s" "%s" "%s"' % (sys.executable, script, executable), env="conanrun")
