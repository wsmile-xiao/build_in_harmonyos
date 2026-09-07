#!/usr/bin/env python3
"""test_package — ogmtools 1.5 L1 test.

ogmtools 是工具集（无公开库 ABI），L1 测试 = 实际执行被测二进制（R34）：
1. 6 个工具 --version 输出 1.5（构建产物可执行 + Conan 依赖链解析）
2. 最小 OGM 容器文件 → ogminfo/ogmsplit 数据处理路径（非空壳）

测试逻辑固化为已提交的源文件 l1_test.sh（CI L0c 静态扫描要求 test_package/
下有真实测试源文件）；test() 仅做占位符替换（@BINDIR@/@WORKDIR@）后执行。
"""
import os

from conan import ConanFile
from conan.tools.env import VirtualRunEnv
from conan.tools.files import load, save
from conan.tools.layout import basic_layout


class OgmtoolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        # 测试产物隔离到 build_folder，避免就地落盘污染配方目录
        basic_layout(self, src_folder=".")

    def generate(self):
        # 运行时环境：被测二进制动态链接 libogg/libvorbis/libdvdread（Conan 提供）
        VirtualRunEnv(self).generate()

    def test(self):
        if self.settings.get_safe("os") == "Windows":
            self.output.warning("ogmtools 测试仅支持类 Unix 平台，跳过")
            return
        bindir = self.dependencies["ogmtools"].cpp_info.bindirs[0]
        workdir = self.build_folder
        # 读取已提交的测试源文件，替换占位符后写入工作目录执行
        script_src = load(self, os.path.join(self.source_folder, "l1_test.sh"))
        script = script_src.replace("@BINDIR@", bindir).replace("@WORKDIR@", workdir)
        path = os.path.join(workdir, "l1_test.sh")
        save(self, path, script)

        self.run(f"sh {path}", env="conanrun")
        self.output.success("ogmtools 1.5 test_package: 全部通过")
