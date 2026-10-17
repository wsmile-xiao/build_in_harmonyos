#!/usr/bin/env python3
"""Conan test_package — pari-nflistdata/20220729（纯数据包，R34 打包内容级校验）.

本包无库、无二进制、包内无上游自动化测试（上游测试入口的实证与逐用例记录见
同级 MANIFEST.yml 与版本目录的 ../upstream-test-cases.txt）。唯一的可验证交付物
是打包进 `<pkg>/res/pari/nflistdata/` 的 678 个数据文件。

测试对被测包**真实内容**做字节级校验（非打印空壳）：条目数/总字节/每度 QT 计数/
A5 分片存在性/整体与分类拼接 sha256/14 个单文件 sha256/GP 语法全量校验/
JR 表完备性哨兵（含 README 声明的 524286 与 10000 边界值）/意外文件与空文件检测。
丢、错、换任一字节都会让 test_pari_nflistdata.py 返回非 0，conan create 的 test
阶段即失败。

不在此处调用 gp/nflist：跑 gp 属首次执行外部二进制，会触发平台安全确认弹窗（R7），
可能挂住 CI；上游功能入口的实跑证据见 MANIFEST.yml 的 consumer_functional_test。
"""
import os
import sys

from conan import ConanFile


class PariNflistdataTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def configure(self):
        self.settings.rm_safe("os.version")
        self.settings.rm_safe("compiler.cppstd")

    def test(self):
        pkg = self.dependencies["pari-nflistdata"].package_folder
        script = os.path.join(self.source_folder, "test_pari_nflistdata.py")
        # R34：校验被测包真实打包内容。数据校验与 host 架构无关，用 sys.executable
        # 直接执行（不依赖 PATH 上的 python3，符合 R33）。
        self.run('"%s" "%s" --package-root "%s"'
                 % (sys.executable, script, pkg), env="conanrun")
