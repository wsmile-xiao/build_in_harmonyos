#!/usr/bin/env python3
"""Conan test_package for xli (consumer perspective, L1).

xli 是 X11 命令行工具（上游无测试套件）。测试在**免显示（headless）**环境下
真实运行本包产出的二进制：

  1. xlito（免显示工具）：把 xli 选项块写入真实图片文件，再读回校验
  2. xli：以 -help 交互模式启动并正常退出（验证二进制与 X11 依赖链可加载）
  3. 断言输出内容确属 xli 家族（用法横幅 + 选项表）

上游测试清点（R51）：xli 1.17.0 源码树无 tests/ 目录、无 check 目标
（Makefile.std 仅有 std/sysv/gcc/install/clean 等目标），故本包测试为
鸿蒙特有消费者测试，N=1（上游 0 + 本包 1）。
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class XliTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        pass

    def test(self):
        bindir = self.dependencies[self.tested_reference_str].cpp_info.bindirs[0]
        script = os.path.join(self.source_folder, "test_xli_consumer.sh")
        # R34: 测试必须实际执行被测包的二进制（xlito/xli），而非仅打印字符串
        self.run(f'bash "{script}" "{bindir}"', env="conanrun")
