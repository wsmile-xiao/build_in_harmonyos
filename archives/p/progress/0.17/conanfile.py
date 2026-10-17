#!/usr/bin/env python3
import os
from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


class ProgressConan(ConanFile):
    name = "progress"
    version = "0.17"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    # 依赖：ncurses（progress 的 Makefile 用 pkg-config 检测 ncursesw——
    # registry 已合入 ncurses/6.5）
    requires = "ncurses/6.5"

    def layout(self):
        basic_layout(self)

    def source(self):
        # 显式下载解压并剥离顶层目录（get strip_root=True——GitHub archive
        # 的顶层目录 progress-0.17/ 被剥离——源码文件【Makefile 等】直接到
        # source_folder 顶层——避免源码布局不确定【CI #21519 报 No targets/
        # makefile found——同 abduco #21461/#21555】
        from conan.tools.files import get
        get(self, self.conan_data["sources"][self.version]["url"],
            sha256=self.conan_data["sources"][self.version]["sha256"],
            strip_root=True)

    def generate(self):
        # progress 的 Makefile 用 pkg-config ncursesw 检测——PKG_CONFIG_PATH
        # 指向 ncurses 包 pkgconfig（alpine/fizmo 的 ncurses 处理先例）
        env = Environment()
        env.append_path("PKG_CONFIG_PATH", os.path.join(
            self.dependencies["ncurses"].package_folder, "lib", "pkgconfig"))
        env.vars(self).save_script("conanbuild_pkgconfig")

    def build(self):
        # progress 无 configure（纯 Makefile 项目——notes.md 确认）；
        # CC=clang：Makefile 默认 CC=cc 但 OHOS 仅有 clang（multitail 先例）；
        # -j1：OHOS 沙箱不支持 mkfifo（jobserver），并行编译失败（opensp 先例）。
        # CFLAGS -I：progress.c 的 #include <curses.h>（CI #21954 报
        # curses.h file not found）——指向 ncurses 包 include 顶层 +
        # include/ncursesw（两种布局——multitail 教训）
        ncurses = self.dependencies["ncurses"]
        ncurses_inc = os.path.join(ncurses.package_folder, "include")
        ncurses_lib = os.path.join(ncurses.package_folder, "lib")
        cflags = f"-I{ncurses_inc} -I{os.path.join(ncurses_inc, 'ncursesw')}"
        # LDFLAGS -L + -lncursesw：链接 ncurses 符号（CI #22098 实测
        # LDLIBS 未生效【progress 的 Makefile 链接规则不引用 LDLIBS——
        # 只有 LDFLAGS 生效】——-lncursesw 加进 LDFLAGS【链接命令
        # $(LDFLAGS) 生效——libncursesw.a 在 ncurses 包 lib】）
        ldflags = f"-L{ncurses_lib} -lncursesw"
        self.run(f"make -j1 CC=clang CFLAGS=\"{cflags}\" "
                 f"LDFLAGS=\"{ldflags}\"",
                 cwd=self.source_folder, env="conanbuild")

    def package(self):
        # Makefile install 支持 DESTDIR+PREFIX（第 33 行 install 目标——
        # Installing program to $(DESTDIR)$(BINDIR)）
        self.run("make install DESTDIR={} PREFIX=/usr".format(
            os.path.join(self.package_folder)), cwd=self.source_folder,
            env="conanbuild")

    def package_info(self):
        self.cpp_info.bindirs = ["usr/bin"]
