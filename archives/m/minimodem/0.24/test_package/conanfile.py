#!/usr/bin/env python3
"""Conan test_package — minimodem 0.24 消费者真跑测试。

两个用例都直接执行包内交付的 bin/minimodem（env="conanrun"），断言逻辑在
同目录静态测试源 test.sh（跟踪入库，兼作 CI L0c 门禁要求的白名单后缀测试源）：
  1. version — `minimodem --version` 自报版本，stdout 含 "minimodem 0.24"
  2. fsk_roundtrip — 300 波特 ASCII FSK 往返（--tx 产生 Bell103 型（300 波特默认）FSK
     WAV → --rx 解调 → 与原文逐字节一致）。
所有测试文件写在测试构建目录（conan 提供的可写目录），不碰 /tmp；
minimodem 本身只读写显式给定的 --file 路径，无临时目录依赖。
OHOS 上 ELF 须经 bash 包装执行（/system/bin/sh (mksh) 不能直接执行 ELF，
2048.c 先例），conan self.run 还会再过一层 shell——两层嵌套引号在 toybox
sh 上实测报 "no closing quote"，所以本文件只负责以参数方式调用
`bash test.sh <minimodem> <workdir>`（参数传递，无内插引号）。
"""

import os

from conan import ConanFile
from conan.tools.build import cross_building


class MinimodemTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: skip run test")
            return
        pkg = self.dependencies["minimodem"]
        bindir = os.path.join(pkg.package_folder, *pkg.cpp_info.bindirs)
        minimodem = os.path.join(bindir, "minimodem")
        assert os.path.isfile(minimodem), "minimodem binary not delivered"

        workdir = self.build_folder
        test_sh = os.path.join(self.source_folder, "test.sh")
        assert os.path.isfile(test_sh), "test_package/test.sh missing"
        self.run('/data/service/hnp/bin/bash "%s" "%s" "%s"'
                 % (test_sh, minimodem, workdir), env="conanrun")
