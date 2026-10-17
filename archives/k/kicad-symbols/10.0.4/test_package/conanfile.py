#!/usr/bin/env python3
"""Conan test_package for kicad-symbols — 消费者视角验证被测包。

本包是纯数据/资源包（无 C/C++ 产物、无 bin/），因此 R34 的“实质依赖”体现为
**真实读取并解析包内数据**：测试脚本从 ``self.dependencies["kicad-symbols"].package_folder``
取出已安装的库表与 223 个打包符号库，逐条校验表↔库一致性、s-expression 完整性、
已知器件（Device:R / Device:C / power:GND / 74xx:74LS00）的引脚数与属性。

负向验证：把包产物移走后本测试必然失败（库表与符号库全部找不到），
即测试确实依赖被测包而非空壳（见 reports/test-report.md）。
"""
import os

from conan import ConanFile


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["kicad-symbols"].package_folder
        script = os.path.join(self.recipe_folder, "test_kicad_symbols.py")
        # 用 shell 形式显式传包目录；-B 避免在只读/HMDFS 路径下写 __pycache__
        self.run('python3 -B "%s" "%s"' % (script, pkg_folder), env="conanrun")
