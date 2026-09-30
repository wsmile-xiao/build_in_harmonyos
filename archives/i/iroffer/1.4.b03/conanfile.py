#!/usr/bin/env python3
"""Conan recipe for iroffer 1.4.b03 — IRC XDCC file server / chat bot (PMG, 2005).

上游是 2005 年的手写 POSIX-sh `Configure`（不是 autoconf/automake）：它探测编译器、
类型宽度与 libc 特性，生成 src/iroffer_config.h 与 Makefile（Makefile 头部的
CC / CONFIG_* 由 Configure 写出，Makefile.config 是它的静态尾巴）。
构建：sh Configure && make，产物是两个可执行文件 iroffer 与 convertxdccfile。
上游没有 install 目标的可用形态（install -o root -g root），也没有测试目标，
所以安装由本配方手工 copy，见 package()。

鸿蒙侧的两处必要改动都在 patches/ 里（不在这里做 sed）：
  1) Configure 的 uname 白名单不含 "HarmonyOS" → 直接 "This OS is not supported"
     并 return（脚本里是裸 exit，退出码还是 0，属于静默失败）。补丁把它映射到
     既有 Linux 分支，让 config.h 落到 #define _OS_Linux（iroffer_defines.h 里
     _OS_Linux 是 _GNU_SOURCE 的唯一开关，其余分支在 OHOS 上都不对）。
  2) Configure 只会找 gcc/cc，鸿蒙 PC 上两者都不存在（只有 clang），于是所有
     特性探测都跑不起来。补丁让它优先采用环境变量 CC，配方从 Conan conf 取值
     后显式传入（R33：不吃裸 shell 环境变量）。
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class IofferConan(ConanFile):
    name = "iroffer"
    version = "1.4.b03"
    description = ("iroffer is an IRC bot / XDCC file server: it joins channels and "
                   "offers files over DCC. Single-file chat daemon by David Johnson (PMG), "
                   "released 2005-12-12.")
    topics = ("irc", "xdcc", "dcc", "chat-bot", "daemon")
    license = "GPL-2.0-or-later"
    homepage = "https://tracker.debian.org/pkg/iroffer"
    url = ""  # CI fills this

    package_type = "application"
    build_policy = "missing"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 上游只链 libc：Configure 的探测结论是 -Wall -O2、无附加 LDLIBS
        # （见生成的 Makefile 头部 CONFIG_LDLIBS 为空），故无 Conan 依赖。
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass  # 纯 makefile 构建，不需要 toolchain 文件

    def build(self):
        apply_conandata_patches(self)

        # R33: 编译器取自 Conan conf，绝不依赖调用方的 shell 环境。
        # ohos-aarch64 profile 把 tools.build:compiler_executables 写成整个 JSON
        # dict，必须整键读取（Conan 2.29 拒绝点分子键）。
        comp = self.conf.get("tools.build:compiler_executables", {}, check_type=dict)
        cc = comp.get("c", "clang")

        # Step 1: Configure —— 打补丁后它优先读 CC，并把结论写进
        # src/iroffer_config.h 与 Makefile。参数最少化（R1）：它只认 -h/-e/-d/-p/-w，
        # 没有 --prefix 概念，一个都不传。
        self.run(f'CC="{cc}" sh ./Configure', cwd=self.source_folder)

        # Step 2: make（R9: -j1）。CC 同时传给 make，覆盖生成 Makefile 里的
        # CC= 行，避免 Configure 与 make 用了两个不同的编译器。
        self.run(f'make all CC="{cc}" -j1', cwd=self.source_folder)

    def package(self):
        # 上游 install 目标是 `install -o root -g root -m 0755 ...`：
        #   a) 鸿蒙 PC 上没有 install 命令（toybox，见 E098）；
        #   b) INSDIR 硬编码 /usr/local/bin，且 chown root 在无根沙箱里必失败（E492 同类）。
        # 所以按 E098 的处方用 copy 落盘。
        bindir = os.path.join(self.package_folder, "bin")
        copy(self, "iroffer", self.source_folder, bindir)
        copy(self, "convertxdccfile", self.source_folder, bindir)

        # 运行期必需的配置样例与随包文档（iroffer 没有可执行就生效的配置）。
        resdir = os.path.join(self.package_folder, "res", "iroffer")
        for doc in ("sample.config", "README", "WHATSNEW", "iroffer.cron", "dynip.sh"):
            copy(self, doc, self.source_folder, resdir)
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["res"]
