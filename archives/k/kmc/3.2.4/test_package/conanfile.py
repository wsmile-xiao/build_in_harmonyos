#!/usr/bin/env python3
"""test_package for kmc 3.2.4 — 消费者视角验证（工具链 + libkmc_core + kmc_runner.h API）。

test() 通过 bash 执行 test.sh（OHOS mksh 无法直接执行 ELF，见模板注释）：
  T1 鸿蒙特有①  aarch64 NEON 基数排序选路（libkmc_core.a 符号断言）
  T2 鸿蒙特有②  OHOS aarch64 ELF + 仅 musl libc 依赖（无 libstdc++ 动态残留）
  T3 上游 fixture 断言复刻（single_read.fq k=28 ci=1 → 70 kmers；issue-180 pattern.dump cmp）
  T4 kmc_tools / kmc_dump 转储链路
  T5 KMC::Runner API 消费者（consumer.cpp，官方发行头 kmc_runner.h 链接 libkmc_core）
"""
import os

from conan import ConanFile


class KmcTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries → use bash.
        bash = os.environ.get("CONFIG_SHELL") or "/data/service/hnp/bin/bash"
        pkg = self.dependencies["kmc"].package_folder
        # R33: 编译器取自 conan conf（本机不支持 `:cpp` 深取 → 先取 dict 再按键）
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = compilers.get("cpp") or "clang++"
        self.run(f'{bash} test.sh "{pkg}" "{cxx}"', env="conanrun")
