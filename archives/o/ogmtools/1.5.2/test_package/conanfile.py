#!/usr/bin/env python3
"""test_package — ogmtools 1.5 L1 test.

ogmtools 是工具集（无公开库 ABI），L1 测试 = 实际执行被测二进制（R34）：
1. 6 个工具 --version 输出 1.5（构建产物可执行 + Conan 依赖链解析）
2. media_roundtrip.py consumer：确定性整数 PCM 经 ogmmerge/ogmcat/ogmsplit/ogmdemux 完整往返逐字节比对

实际入口为已提交的 media_roundtrip.py。consumer 模式为7个用例；OHOS另执行
harmony 模式，以不同输入及HMDFS中文路径、属主投影和精确清理验证独立专项。
废弃的最小空容器 l1_test.sh 已删除，不作为通过证据。
"""
import os
import shlex
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv
from conan.tools.layout import basic_layout


class OgmtoolsTestConan(ConanFile):
    win_bash = True
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
        bindir = os.path.join(self.dependencies["ogmtools"].package_folder, "bin")
        for tool in ("ogmmerge", "ogmdemux", "ogminfo", "ogmsplit", "ogmcat", "dvdxchap"):
            if not os.path.isfile(os.path.join(bindir, tool)):
                raise RuntimeError("missing tested package executable: " + tool)
        if not can_run(self):
            self.output.info("CROSS_BUILD: target execution deferred; no test PASS claimed")
            return
        script = os.path.join(self.source_folder, "media_roundtrip.py")
        for mode in (["consumer", "harmony"] if str(self.settings.os) == "OHOS" else ["consumer"]):
            argv = [sys.executable, script, mode, bindir, self.build_folder]
            self.run(" ".join(shlex.quote(arg) for arg in argv), env="conanrun")
