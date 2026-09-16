#!/usr/bin/env python3
"""Conan recipe - ctronome 0.5.6 (plain Makefile, command line tool).

ctronome 是一个可编程的命令行节拍器：读取两个 WAV 采样作为声音素材，
按 BPM / 拍号循环把音频数据写入 OSS 设备（默认 /dev/dsp）。

构建系统：顶层裸 Makefile（既无 configure 脚本，也无 install / check
目标），因此本配方自行完成编译与打包，不使用 Autotools 辅助类。

OHOS 适配要点
-------------
1. 上游 Makefile 的编译规则写作 CC -c 源文件，完全没有引用 CFLAGS，
   因此所有编译标志只能随 CC 一起传入，单独设置 CFLAGS 是无效的。
   （R33：CC 取自 Conan conf，不裸用 shell 里的 CC 环境变量。）

2. 源码补丁 0001：ctronome.c / dsp.c / routines.c 都 include ctronome.h，
   而 ctronome.h 里直接定义了 programfile、dsp_channels、dsp_format、
   dsp_speed、dsp_depth、debug 等全局变量（2014 年的暂定义写法），依赖
   GCC 10 以前的 common symbol 合并语义。clang 15 默认 -fno-common，每个
   目标文件都落成强定义，链接期 ld.lld 报 12 处 duplicate symbol。
   补丁把这 6 个暂定义改成 extern 声明，并在 ctronome.c 中给出唯一一份
   定义（C99 起的标准做法）。刻意不用 -fcommon 掩盖——知识库 E491 明确
   禁止 -fcommon，它会隐藏非法的声明/定义关系。

3. 音频输出走 OSS（dsp.c）。HarmonyOS PC 没有 /dev/dsp 字符设备，
   ctronome 会打印 FATAL: cannot open dsp device /dev/dsp 后以 1 退出；
   可用 -d device 指定其它 OSS 兼容设备。参数解析、WAV 头解析、节拍模式
   计算等其余功能与平台无关，均正常工作。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.layout import basic_layout


class CtronomeConan(ConanFile):
    name = "ctronome"
    version = "0.5.6"
    description = ("ctronome is a very simple programmable command-line "
                   "metronome with OSS (/dev/dsp) audio output")
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/ctronome/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os 判断必须使用 in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"ctronome supports Linux/OHOS only, got {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: 编译器取自 Conan conf，绝不使用 shell 环境变量。
        # 注意 conf 名是 tools.build:compiler_executables（一个字典），
        # 不能写成 tools.build:compiler_executables:c —— 后者不是已注册的
        # conf 名，self.conf.get() 会抛 ConanException。
        compilers = self.conf.get("tools.build:compiler_executables",
                                  check_type=dict, default={})
        cc = compilers.get("c", "clang") if compilers else "clang"
        # 上游 Makefile 的编译规则不引用 CFLAGS，编译标志只能随 CC 传入；
        # 本包不需要额外标志（duplicate symbol 由补丁 0001 从源码修复）
        self.run(f"make CC=\"{cc}\" -j1", cwd=self.source_folder)

    def package(self):
        copy(self, "ctronome", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "*.wav", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "ctronome"))
        copy(self, "README", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "ctronome"))
        copy(self, "NOTES", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "ctronome"))
        copy(self, "prog_example.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "ctronome"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
