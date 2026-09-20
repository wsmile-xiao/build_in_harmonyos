#!/usr/bin/env python3
"""Conan 2 recipe — ondir 0.2.4 (Alec Thomas, C CLI 工具, 零依赖).

进入/离开目录时自动执行配置脚本的 shell 钩子工具：`ondir <old> [new]`
按 ~/.ondirrc（及 GLOBAL_CONF）的 enter/leave 正则规则把待 eval 的 shell
命令打印到 stdout，由 shell 钩子 eval。产物: bin/ondir +
share/man/man1/ondir.1 + share/ondir/{scripts.sh,scripts.tcsh,scripts.zsh,ondirrc.eg}。

OHOS 适配要点：
- 官方 dist tarball（swapoff.org），纯手写 Makefile（非 autotools）——
  无 configure/config.h/codegen，CC 覆盖即编（conf.c + ondir.c 两单元）。
- 依赖仅 POSIX libc：regex.h（musl 提供）、limits.h PATH_MAX。
- 上游 Makefile CFLAGS 两行后者生效：`-Wall -c -g -DVERSION -DGLOBAL_CONF`
  （无 USE_ONENTERLEAVE——上游标注 "not recommended at all"，保持默认关）。
- GLOBAL_CONF 编译期固化 /etc/ondirrc；运行时 HOME/.ondirrc 覆盖可用，
  测试经 HOME 隔离（HMFS /etc 只读不写全局配置）。

层1 上游测试：上游无测试套件（无 tests/、无 check 目标）——build() 内
做 smoke 验证（ondir -V 输出版本号）；功能性 enter/leave 正则规则测试
在 test_package 以断言形式补齐（见 MANIFEST.yml）。
"""

from conan import ConanFile
from conan.tools.files import copy, get
import os


class OndirConan(ConanFile):
    name = "ondir"
    version = "0.2.4"
    description = "进入/离开目录时自动执行脚本命令的 shell 钩子工具 (OnDir)"
    license = "GPL-2.0-or-later"
    homepage = "https://swapoff.org/ondir.html"
    url = ""  # CI fills this
    topics = ("shell", "directory", "automation", "cli")

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        # R33: 编译器从 conan conf 取（CI 上 $CC 为空）
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"

        src = str(self.source_folder)
        bf = str(self.build_folder)

        # 上游 Makefile：CC 覆盖为 conan 编译器；CONF 固化 /etc/ondirrc
        # （上游默认）；构建产物落在 source_folder（Makefile 无 out-of-tree
        # 支持，两文件直接编译链接）。
        # 链接规则用 $(LD)（上游 LD=cc 与 CC 分离），只覆盖 CC 会导致 CI 上
        # 链接步找裸 cc 失败（Error 127，CI #44149）→ CC/LD 都覆盖。
        self.run(f'make -C "{src}" CC="{cc}" LD="{cc}"', env="conanbuild")
        copy(self, "ondir", src=src, dst=bf)

        # 层1 smoke：上游无测试套件，-V 版本输出为唯一自证路径
        self.run(f"./ondir -V", cwd=bf)

    def package(self):
        src = str(self.source_folder)
        pkg = str(self.package_folder)
        copy(self, "ondir", src=self.build_folder,
             dst=os.path.join(pkg, "bin"))
        copy(self, "ondir.1", src=src,
             dst=os.path.join(pkg, "share", "man", "man1"))
        copy(self, "scripts.sh", src=src, dst=os.path.join(pkg, "share", "ondir"))
        copy(self, "scripts.tcsh", src=src, dst=os.path.join(pkg, "share", "ondir"))
        copy(self, "scripts.zsh", src=src, dst=os.path.join(pkg, "share", "ondir"))
        copy(self, "ondirrc.eg", src=src, dst=os.path.join(pkg, "share", "ondir"))
        copy(self, "COPYING", src=src,
             dst=os.path.join(pkg, "licenses"))

    def package_info(self):
        # 命令行工具：为下游 VirtualRunEnv 暴露 bin/
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
