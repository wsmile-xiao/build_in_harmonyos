#!/usr/bin/env python3
"""Conan test_package for xmcd (consumer perspective, L1).

xmcd 是 Motif GUI CD 播放器/抓轨工具，同时产出命令行工具 cda 与 CDDB 浏览器
gobrowser。上游无测试套件，本包在**免显示（headless）**环境下真实运行产出的
二进制：

  1. cda（CLI）：-h 打印版本横幅与用法，验证二进制与 ncurses/线程库依赖链
  2. xmcd（Motif GUI）：无 X 显示时启动并报 "Can't open display"，
     验证二进制与 Motif/Xt/X11/SM/ICE 依赖链已被动态加载器成功解析
  3. 两条路径均断言不出现 "Error loading shared library"（链接期缺库会在此暴露）

上游测试清点（R51）：xmcd 3.3.2 源码树无 tests/ 目录，Makefile.std 仅含
std/sysv/gcc/Makefiles/all/install/clean 等目标，无 check/test；故本包测试
为鸿蒙特有消费者测试，N=1（上游 0 + 本包 1）。
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class XmcdTestConan(ConanFile):
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
        script = os.path.join(self.source_folder, "test_xmcd_consumer.sh")
        # R34: 测试必须实际执行被测包的二进制（cda/xmcd），而非仅打印字符串
        self.run(f'bash "{script}" "{bindir}"', env="conanrun")
