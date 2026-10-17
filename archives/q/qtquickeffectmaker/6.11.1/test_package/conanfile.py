#!/usr/bin/env python3
"""Conan test_package — qtquickeffectmaker 6.11.1 L1 test.

L1 test:
1. 编译并运行 test.c——最小消费者程序（L0c 要求 test_package 有测试
   源文件，上游不产出 C++ 链接库故无库可链接）；
2. 运行包内 qqem 应用（--help）验证可执行（鸿蒙 ELF 签名后）；
3. 验证 QML 模块（QtQuickEffectMaker/defaultnodes 节点资源）随包安装。

说明：上游 qtquickeffectmaker 不产出 C++ 链接库（src/ 仅 doc，
安装产物为 qqem 应用 + QML 节点资源，无 libQt6QuickEffectMaker.so 与
Qt6QuickEffectMakerConfig.cmake），故消费者测试采用应用级验证。
"""
import os

from conan import ConanFile


class QtquickeffectmakerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # 编译最小消费者程序（L0c 测试源文件载体）
        ccs = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cc = ccs.get("c") or "clang"
        src = os.path.join(self.source_folder, "test.c")
        out = os.path.join(self.build_folder, "test_qqem")
        self.run(f"{cc} {src} -o {out}")

    def test(self):
        # 最小消费者程序运行
        exe = os.path.join(self.build_folder, "test_qqem")
        self.run(exe)
        # 应用验证：qqem 可执行（offscreen 平台）
        qqem = os.path.join(
            self.dependencies["qtquickeffectmaker"].package_folder, "bin", "qqem")
        self.run(f"test -x {qqem}")
        self.run(f"QT_QPA_PLATFORM=offscreen {qqem} --help", env="conanrun")
        # QML 节点资源随包安装
        nodes = os.path.join(
            self.dependencies["qtquickeffectmaker"].package_folder,
            "qml", "QtQuickEffectMaker", "defaultnodes")
        self.run(f"test -d {nodes}")
