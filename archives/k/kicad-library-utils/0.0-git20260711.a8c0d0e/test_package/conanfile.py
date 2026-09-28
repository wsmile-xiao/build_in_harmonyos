#!/usr/bin/env python3
"""Conan test_package for kicad-library-utils — 消费者视角真实运行上游测试。

本包的上游自带官方测试（上游仓库 Makefile，unittest 体系，纯标准库，无需
pytest）：

  * make test-klc-symbols:
      python3 klc-check/check_symbol.py --unittest klc-check/test_symbol/*.kicad_symdir
  * make test-klc-footprints:
      python3 klc-check/check_footprint.py --unittest klc-check/test_footprint.pretty/*__*.kicad_mod
      python3 klc-check/check_footprint.py -vv klc-check/test_footprint.pretty/SO-8_3.9x4.9mm_P1.27mm.kicad_mod
  * make test-symgen:
      symbol-generators/from_csv_generator.py symbol-generators/BQ24004-example.csv

test() 从 self.dependencies 取出被测包的 package_folder，交给 test_klc_check.py
在 OHOS 真机上按上游 Makefile 原样执行上述命令。python3 -B 关闭字节码写入，
保持已安装包目录卫生（不在包内遗留 __pycache__）。
"""
import os

from conan import ConanFile


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["kicad-library-utils"].package_folder
        script = os.path.join(self.recipe_folder, "test_klc_check.py")
        self.run('python3 -B "%s" "%s"' % (script, pkg_folder), env="conanrun")
