#!/usr/bin/env python3
"""test_package for trinculo — 消费已安装 CLI 的真实功能断言。

不用 cmake_layout（无编译面）：basic_layout 把 env 脚本/输出隔离到 build
目录（device-facts §5.3：必须定义 layout()，否则 build==source 脚本落包源树）。
夹具从**包体** share/trinculo/examples 取（随包 PLINK 样例，含 .bed），
输出写 build_folder 下临时目录（§一.1 绝对路径/可写域）。
"""
import os
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.layout import basic_layout


class TrinculoTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["trinculo"]
        binpath = os.path.join(pkg.package_folder, "bin", "trinculo")
        exdir = os.path.join(pkg.package_folder, "share", "trinculo", "examples")
        work = tempfile.mkdtemp(prefix="trinculo-tp-", dir=self.build_folder)
        out_file = os.path.join(work, "tp.out")
        test_py = os.path.join(self.source_folder, "test_trinculo.py")

        # self.run 返回 None（device-facts §5.3）→ 重定向回读；N==0 同样判失败。
        # python3 走 sys.executable 绝对路径（§一.14 裸命令名）。
        import sys
        cmd = '"{0}" "{1}" "{2}" "{3}" "{4}" > "{5}" 2>&1 || exit 1'.format(
            sys.executable, test_py, binpath, exdir, work, out_file)
        self.run(cmd, env="conanrun")
        out = open(out_file, encoding="utf-8", errors="replace").read()
        self.output.info(out)
        if "FAIL - " in out:
            raise ConanException("test_package 有断言失败（见上方 FAIL 行）")
        n_pass = out.count("PASS - ")
        if n_pass == 0:
            raise ConanException("test_package 输出无任何 PASS 行（N==0 假绿）")
        self.output.info("test_package: {} assertions, 0 failed".format(n_pass))
