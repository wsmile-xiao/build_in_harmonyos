#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""swe-data 4.0-20221111 test_package —— 纯数据包，无需编译。

两级验证：

① **完整消费者用例（平台 rule12）**：`consumer_ephe.py` 按 libswe / swetest 的
   真实取数方式把交付数据消费一遍 —— 数据目录契约（SE_EPHE_PATH）→ 182 个
   `*.se1` 的头部解析与 CRC-32 完整性 → 按世纪规则定位文件 → 读取该历元的
   Chebyshev 段并解包 → 赤道面旋转 → 求值得到日心/地心位置矢量 → 与**上游参考
   实现**（libswe 2.10.03 的 `swetest`，配本数据包）的参照值逐项比对，
   外加行星卫星到中心体距离与文档半长轴比对、文本表按下游真实用法解析。
   实测 172 项检查全部通过。

② **适配自检（M=16）**：`test_ephe.py` —— 安装布局（与 Debian
   usr/share/libswe/ephe 同形）、文件清点、载荷长度/字节数/DE431、文件名与
   内容自洽、许可与文档交付、安装纯净性。

上游 N=0：源包内只有数据文件与指向 Debian 打包目录的符号链接，没有测试目录、
没有测试框架、没有 `check`/`test` 目标，Debian 源包也没有 autopkgtest。
"""
import os
import sys

from conan import ConanFile


class SweDataTestConan(ConanFile):
    # 纯数据包：无编译、无 settings（载荷与架构无关，Debian 亦为 Architecture: all）

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["swe-data"].package_folder

        # ① 完整消费者用例（平台 rule12）：端到端取数并与上游 swetest 参照值比对
        consumer = os.path.join(self.source_folder, "consumer_ephe.py")
        self.run(f"{sys.executable} {consumer} {package_folder}")

        # ② 适配自检（M，非上游用例；上游 N=0）
        script = os.path.join(self.source_folder, "test_ephe.py")
        self.run(f"{sys.executable} {script} {package_folder}")
