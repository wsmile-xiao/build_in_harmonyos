#!/usr/bin/env python3
"""kacst_fonts 2.01 test_package —— 纯数据包，无需编译。

完整消费者用例（平台 rule12）：`consumer_fonts.py` 按文本栈/fontconfig 的取用方式消费
本包 —— 按 XDG 约定定位 `share/fonts/truetype/kacst/`，**解析每套 TrueType 字体的真实表**
（`head`/`maxp`/`name`/`cmap`，纯 Python 不依赖 freetype），再用样本串做**码点覆盖 →
字体选择**：阿拉伯文样本必须被完全覆盖、家族名不得重复、映射的字形 id 不得越界，
并按事实记录"拉丁/ASCII 数字不被本字体集覆盖"这一消费结论（需回退其它家族）。

上游 N=0：源包内无 `test/`/`tests/`、无 `check`/`test` 目标、无 `debian/tests/`；
Debian 源包 fonts-kacst 只做字体安装（`debian/rules` 是 dh + fontconfig 片段）。
"""
import os
import sys

from conan import ConanFile


class KacstFontsTestConan(ConanFile):
    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["kacst_fonts"].package_folder

        # ① 完整消费者用例（平台 rule12）：表解析 → 码点覆盖 → 字体选择
        consumer = os.path.join(self.source_folder, "consumer_fonts.py")
        self.run(f"{sys.executable} {consumer} {package_folder}")

        # ② 适配自检（M=7，非上游用例；上游 N=0）
        script = os.path.join(self.source_folder, "test_fonts.py")
        self.run(f"{sys.executable} {script} {package_folder}")
