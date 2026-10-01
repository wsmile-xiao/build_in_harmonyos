#!/usr/bin/env python3
"""Conan test_package — vgabios 0.8a

实质消费被测包（R34）：
  * 读取包内 share/vgabios/ 的 5 个 8086 Option ROM，逐字节校验其结构
    （0x55AA 签名、ROM 校验和、长度字段、PCIR 结构、变体标记）；
  * 实际运行包内 bin/biossums，对被人为破坏的 ROM 做校验和修复。

测试逻辑与用例统计见 test_vgabios.sh（L0c 门禁要求 test_package/ 有测试源文件）。
"""
import os

from conan import ConanFile


class VgabiosTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["vgabios"].package_folder
        script = os.path.join(self.source_folder, "test_vgabios.sh")
        # OHOS: /system/bin/sh (mksh) 无法执行 ELF 二进制；用 bash 作为包装器
        bash = "/data/service/hnp/bin/bash"
        if not os.path.exists(bash):
            bash = "bash"
        self.run(f'{bash} "{script}" "{pkg}"')
