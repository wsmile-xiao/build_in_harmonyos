#!/usr/bin/env python3
"""Conan test_package for mrc 1.3.17.

mrc 是命令行工具（资源编译器）——测试方式为**真实执行** mrc 二进制：
用 test_package 自带的资源文件生成 .obj，验证编译器可用（R34）。

具体校验由 `run_mrc_tests.sh` 执行（同时满足 CI 门禁 L0c 对"测试源文件"的要求），
内容包括：mrc 退出码 0、产物非空、产物为 ELF relocatable/AArch64、产物内嵌资源
载荷文本、产物导出 mrc 约定的 gResource 符号。
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building


class MrcTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: skipping runtime execution")
            return
        rsrc = os.path.join(self.source_folder, "hello.txt")
        # 产物输出到 build_folder 下的**临时子目录**，而不是直接落在 test_package/：
        #   ① 避免污染源码目录（CI 工作区 dirty）；
        #   ② 避免产物被误提交入库（R19 禁止 PR 携带预编译二进制）。
        out_dir = os.path.join(self.build_folder, "_mrc_test")
        script = os.path.join(self.source_folder, "run_mrc_tests.sh")

        # Conan 2 的 self.run() 不返回输出 → 重定向到文件后再读
        log = os.path.join(self.build_folder, "mrc_tests.log")
        self.run(
            f'sh "{script}" "mrc" "{rsrc}" "{out_dir}" > "{log}" 2>&1',
            env="conanrun")
        with open(log, encoding="utf-8", errors="replace") as f:
            result = f.read()
        self.output.info(result.strip())

        m = re.search(r"RESULT: passed=(\d+) failed=(\d+)", result)
        if not m:
            raise ConanException("mrc: 未取得测试汇总行")
        passed, failed = int(m.group(1)), int(m.group(2))
        if failed or not passed:
            raise ConanException(
                f"mrc: 消费者功能测试未通过（passed={passed} failed={failed}）")
        self.output.info(f"mrc OK（{passed} 项校验通过）")

