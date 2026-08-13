#!/usr/bin/env python3
"""Conan recipe for tty-clock 2.3 — TTY 终端时钟（纯 Makefile 构建）。

Build system: 上游 Makefile（非 autotools，无 configure）。
依赖：ncurses 6.5（静态库，OHOS 必须静态；--without-shared 编译，
     libs = ncursesw/panelw/menuw/formw）。
补丁：0001-Makefile.patch 增加 ncursesw6-config 检测分支
     （OHOS 提供 ncursesw6-config(v6) 而非 v5；硬编码
     -I${PREFIX}/include -L${PREFIX}/lib -lncursesw）。
OHOS 注意：无 make check 测试目标；ncursesw 静态链接内置 stale staging
     terminfo 路径，运行期需 TERMINFO 修复（见 notes.md）。
"""
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    copy,
)
from conan.tools.layout import basic_layout


class TtyClockConan(ConanFile):
    name = "tty-clock"
    version = "2.3"
    description = "A terminal clock for the terminal (ncurses)."
    license = "GPL-3.0"
    homepage = "https://github.com/xorg62/tty-clock"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # OHOS 必须静态 ncurses（ncurses 配方在 OHOS 拒绝 shared）
        self.requires("ncurses/6.5", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # tty-clock 的 Makefile 检测链（ncurses5/w5/w6-config → pkg-config）
        # 在 conan 环境全部不可用，落到 else 分支 `pkg-config ncurses`，
        # 而 ncurses 6.5 配方的 pkg_config_name 是 ncursesw → 找不到。
        # 因此直接通过环境变量提供头文件/库路径；但 Environment 对
        # LDFLAGS 类 flag 变量用 ":" join 会破坏参数，故此处只注入
        # CFLAGS（Makefile 的 CFLAGS += 依赖它），LDFLAGS 在 build() 传。
        env = Environment()
        for dep in self.dependencies.values():
            for incdir in dep.cpp_info.includedirs:
                env.append_path("CFLAGS", f"-I{incdir}")
        env.vars(self).save_script("conanbuildenv")

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang") if compilers else "clang"
        # ncurses 6.5 静态库：-lncursesw（配方的 cpp_info.libs[0]）
        dep = self.dependencies["ncurses"]
        cflags = " ".join(f"-I{inc}" for inc in dep.cpp_info.includedirs)
        cflags += " -Wall -g -DNCURSES_WIDECHAR"
        ldflags = " ".join(f"-L{lib}" for lib in dep.cpp_info.libdirs)
        ldflags += " -lncursesw"
        # 上游 Makefile 无 configure；PREFIX 仅影响 install 路径。
        # 命令行 CFLAGS/LDFLAGS 覆盖 Makefile 内赋值（+= 对命令行变量无效），
        # 故显式带上 ncurses 头文件路径与 -Wall -g。
        self.run(
            f"make -j1 CC={cc} PREFIX=/usr "
            f"CFLAGS='{cflags}' LDFLAGS='{ldflags}'"
        )

    def package(self):
        # PREFIX 留空：DESTDIR 直接落包根（bin/tty-clock、share/man/...），
        # 同 abduco 先例；STRIP=true 保持未 strip（OHOS MAC 拒绝 stripped 二进制）。
        self.run(
            "make install PREFIX= MANPREFIX=share/man DESTDIR={} STRIP=true".format(
                self.package_folder
            )
        )
        copy(self, "LICENSE*", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
