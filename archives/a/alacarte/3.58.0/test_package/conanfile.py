#!/usr/bin/env python3
"""Conan test_package for alacarte — Python 级验证（L1 official test）。

alacarte 是纯 Python GTK 应用（上游无任何测试框架/用例，CI 仅跑
make distcheck）。test_package 提供真实测试源文件 test_alacarte.py
（L0c + R34 合规）：
  1. 语法编译校验所有交付 .py（py_compile）
  2. 以 mock gi/gi.repository 加载被测包 Alacarte.util，验证核心纯逻辑
     （唯一文件名生成 / KeyFile 填充）
  3. 断言包结构（bin/alacarte 可执行 + site-packages 模块齐全）

CI 通过 `conan create` 自动调用本 test()（L1）。
"""
import os

from conan import ConanFile


class AlacarteTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["alacarte"].package_folder
        site = os.path.join(pkg, "lib", "python3.12", "site-packages")
        # L1 负向测试防护: 必须加载被测包内的 Alacarte (R34)——断言
        # Alacarte.util.__file__ 以 pkg 路径开头, 证明 test 真实依赖被测包。
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_alacarte.py")
        # 不用 env="conanrun": gtk 依赖链的 gettext libintl 进入 LD_LIBRARY_PATH
        # 会与系统 python 的 libintl_* 符号风格冲突 (libintl_gettext symbol not
        # found), 纯 Python 测试仅需系统 python + PYTHONPATH 指向被测包。
        self.run(f"PYTHONPATH='{site}' python3 '{test_script}' '{pkg}'")
