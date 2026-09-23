#!/usr/bin/env python3
"""Conan test_package — povray 3.7.0.10.

消费者视角验证（L1 级，R34 实质断言）。测试逻辑（12 项断言）在独立驱动
test_povray.py 中，本 test() 通过 self.run() 调用：
  1. banner：`povray --version` 输出含 "Persistence of Vision" 与 "3.7.0.10"
  2. 真实渲染：test.pov（相机+光源+棋盘格平面+球，#include "colors.inc"
     场景库）→ 64x64 PNG，断言退出码/PNG 魔数/IHDR 尺寸/bit_depth/color_type/
     Trace Time 统计行；+L 指向包内 share/povray-3.7/include 验证场景库布局

驱动独立成文件的原因：CI L0 质量门禁按扩展名（.c/.cpp/.sh/.py 等）识别
test_package/ 的测试源文件，conanfile.py 本身不计入——断言逻辑放
test_povray.py 后 L0c 才能通过（参考 swftools 0.9.2 的 test_swftools.py）。
"""
import os
import sys

from conan import ConanFile


class PovrayTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # 无需编译：测试直接驱动包内 povray 渲染器
        pass

    def test(self):
        povray_dep = self.dependencies["povray"]
        pkg = str(povray_dep.package_folder)
        povray_bin = os.path.join(pkg, "bin", "povray")
        include_dir = os.path.join(pkg, "share", "povray-3.7", "include")
        test_pov = os.path.join(self.source_folder, "test.pov")
        driver = os.path.join(self.source_folder, "test_povray.py")

        assert os.path.isfile(driver), "test driver test_povray.py missing"

        # 断言逻辑全在驱动脚本内；驱动自身把输出写进临时目录，
        # 不会污染 test_package/ 源目录（E600 教训）。
        self.run('"%s" "%s" "%s" "%s" "%s"'
                 % (sys.executable, driver, povray_bin, test_pov, include_dir))
