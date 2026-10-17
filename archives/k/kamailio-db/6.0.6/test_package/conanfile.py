#!/usr/bin/env python3
"""Conan test_package — kamailio-db 6.0.6 L1 消费者视角测试（OHOS PC）。

被测产物是 33 个 kamailio 运行期 dlopen 的模块插件（非可链接库），L1 测试围绕
「产物结构 + 目标平台（鸿蒙）ABI 契约 + 动态加载器实测」展开：

  check_db_modules.py（自解析 ELF，全部断言基于真实字节）
    [1]  33/33 模块齐全性
    [H1] OHOS ABI 契约        ELF64 / AArch64 / ET_DYN            （鸿蒙特有）
    [H2] OHOS 依赖自洽        DT_NEEDED ⊆ {libc.so}               （鸿蒙特有）
    [H3] RPATH 卫生           无 RPATH/RUNPATH
    [H4] kamailio 模块接口    自解析 exports->name 逐一比对模块名
    [H5] 模块目标标识         kamailio 6.0.6 (aarch64/linux)       （鸿蒙特有）
    [H6] 编译标志集合一致     无 USE_SCTP / HAVE_RESOLV_RES        （鸿蒙特有）
    [7]  许可证随包
  dlopen_probe.c
    [H7] OHOS 加载器实测      真实 dlopen 全部 33 个 .so            （鸿蒙特有）
"""
import os
import sys

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.env import Environment


class KamailioDbTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        # 生成物（编译的探针）落到 build/，保持 test_package 源码目录干净
        self.folders.build = "build"
        self.folders.generators = os.path.join("build", "generators")

    def test(self):
        pkg = self.dependencies[self.tested_reference_str].package_folder
        tp = os.path.dirname(os.path.abspath(__file__))
        checker = os.path.join(tp, "check_db_modules.py")

        # 结构 + ABI + 契约（含鸿蒙特有 [H1]/[H2]/[H5]/[H6]）
        env = Environment()
        env.define("KAMAILIO_DB_PACKAGE_FOLDER", pkg)
        with env.vars(self).apply():
            self.run(f'"{sys.executable}" "{checker}"')

        if cross_building(self):
            self.output.info("cross-building：跳过 [H7] 运行期 dlopen 实测")
            return

        # [H7] OHOS 动态加载器实测（鸿蒙特有）
        cc = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ).get("c", "clang")
        probe_src = os.path.join(tp, "dlopen_probe.c")
        probe = os.path.join(self.build_folder, "dlopen_probe")
        self.run(f'{cc} -O1 -o "{probe}" "{probe_src}"')
        mods = os.path.join(pkg, "lib", "kamailio", "modules")
        self.run(f'"{probe}" "{mods}"')
