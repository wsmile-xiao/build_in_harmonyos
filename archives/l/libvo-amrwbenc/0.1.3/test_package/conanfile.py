#!/usr/bin/env python3
"""libvo-amrwbenc 0.1.3 test_package —— 真实消费者（含参考解码器闭环）。

① **完整消费者用例（平台 rule12）**：`test_vo_amrwbenc.c` 生成真实 WAV →
   用交付的 `bin/amrwb-enc` 编码 → 校验码流结构（魔数/帧数/帧长/帧头 FT）→
   用库 API 编码并与 CLI 产物逐字节比对 → 遍历 9 种模式 → 用同源参考解码器
   （opencore-amr/0.1.6，仓库已适配）解码回 PCM 做相关性/SNR 闭环校验。
② **适配自检（M）**：`test_layout.py` 检查交付形态（库/头/pkg-config/工具/许可/纯净性）。

解码侧用 opencore-amr 是本仓库已有的适配包（AMR-WB 解码器与 vo-amrwbenc 同源），
这样消费者用例覆盖的是「编码 → 解码」整条真实链路，而不只是编码器自身。
"""
import os
import sys

from conan import ConanFile
from conan.tools.build import cross_building


class LibvoAmrwbencTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "PkgConfigDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 参考解码器：AMR-WB 解码由同源的 opencore-amr 提供（仓库已适配 0.1.6）
        self.requires("opencore-amr/0.1.6")

    def build(self):
        dep = self.dependencies["libvo-amrwbenc"]
        dec = self.dependencies["opencore-amr"]
        includes = ["-I" + p for p in dep.cpp_info.includedirs]
        includes += ["-I" + p for p in dec.cpp_info.components["amrwb"].includedirs]
        libdirs = ["-L" + p for p in dep.cpp_info.libdirs]
        libdirs += ["-L" + p for p in dec.cpp_info.components["amrwb"].libdirs]
        conf = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = conf.get("c", "clang")
        self.run(
            "{cc} -O2 {inc} test_vo_amrwbenc.c -o test_probe {lib} "
            "-lvo-amrwbenc -lopencore-amrwb -lm".format(
                cc=cc, inc=" ".join(includes), lib=" ".join(libdirs)))

    def test(self):
        package_folder = self.dependencies["libvo-amrwbenc"].package_folder
        cli = os.path.join(package_folder, "bin", "amrwb-enc")
        workdir = os.path.join(self.build_folder, "consumer-work")
        os.makedirs(workdir, exist_ok=True)
        if cross_building(self):
            self.output.info("cross-building：只验编译 + 链接（原生构建时才会执行）")
        else:
            self.run("{probe} {cli} {workdir}".format(
                probe=os.path.join(self.build_folder, "test_probe"),
                cli=cli, workdir=workdir), env="conanrun")
        # 适配自检（M，非上游用例）
        layout = os.path.join(self.source_folder, "test_layout.py")
        self.run("%s %s %s" % (sys.executable, layout, package_folder))
