#!/usr/bin/env python3
"""Conan test_package — tccutil 1.5.1 消费者验证。

tccutil 为纯 Python 命令行工具（无 C 库/头文件），test() 直接调用被测包
产物 bin/tccutil 的真实 CLI 路径与模块 API：

  1. bin/tccutil --version：真实执行 main()/display_version()，断言输出
     含 "1.5.1" 且退出码 0
  2. bin/tccutil --help：真实执行 argparse 帮助路径，断言退出码 0
  3. import 模块 API：SourceFileLoader 加载 bin/tccutil（无 .py 后缀，
     spec_from_file_location 无法推断 loader），断言
     util_version == '1.5.1'、display_version/display_help 可调用

断言脚本 test_tccutil.py 自行统计 discovered/passedCount 并输出
HMBS_TEST_PACKAGE_RESULT 标记；上游无测试套件（见 MANIFEST.yml 审计），
输出 HMBS_UPSTREAM_TEST_RESULT=no_tests 标记。
"""
import os

from conan import ConanFile


class TccutilTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies[self.tested_reference_str].package_folder
        script = os.path.join(self.source_folder, "test_tccutil.py")
        self.run("python3 {} {}".format(script, pkg), env="conanrun")
