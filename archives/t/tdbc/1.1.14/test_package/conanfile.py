#!/usr/bin/env python3
"""Conan test_package — tdbc/1.1.14 消费者测试。

tdbc 是 Tcl 扩展包（不是 C 库）：消费方式是 tclsh 经 auto_path / TCLLIBPATH
找到 lib/tdbc1.1.14/pkgIndex.tcl 并 dlopen libtdbc1.1.14.so。因此这里不编译
C 程序，而是真实加载被测包并调用其 API（R34）。

入口为 test_tdbc.sh（CI L0c 要求的测试源文件），其内部以 tclsh8.6 执行
test_tdbc.tcl 中的断言。
"""
import os

from conan import ConanFile


class TdbcTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        script = os.path.join(self.recipe_folder, "test_tdbc.sh")
        # 环境来源（均由 Conan 依赖链注入）：
        #   tcl/8.6.16 runenv  → PATH += <tcl>/bin（tclsh8.6）、LD_LIBRARY_PATH += <tcl>/lib
        #   tdbc/1.1.14 runenv → TCLLIBPATH += <tdbc>/lib
        self.run(f'sh "{script}"', env="conanrun")
