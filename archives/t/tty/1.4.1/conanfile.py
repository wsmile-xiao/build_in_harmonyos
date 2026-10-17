#!/usr/bin/env python3
"""Conan recipe for tty 1.4.1 — TTY 终端纸牌接龙游戏（纯 Makefile 构建）。

Build system: 上游 Makefile（非 autotools，无 configure，BUILD_SYSTEM=makefile）。
依赖：ncurses/6.5（静态库，OHOS 必须静态；-lncursesw 宽字符 + -DNCURSES_WIDECHAR）。
命令行 CFLAGS/LDFLAGS 覆盖 Makefile 内赋值（+= 对命令行变量无效），
故显式带上 -std=c99/-DVERSION/ncurses 头文件与库路径。
产物：bin/ttysolitaire（CLI 可执行，package_type=application）。
上游测试：`make test`（67 个具名测试函数/115 个断言，tests/ttysolitaire_test.c 入口），
在 build() 内实际执行，作为 CI 可见的上游测试证据。
"""
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    copy,
)
from conan.tools.layout import basic_layout


class TtySolitaireConan(ConanFile):
    name = "tty"
    version = "1.4.1"
    description = "Ncurses-based klondike solitaire game for the terminal."
    license = "MIT"
    homepage = "https://github.com/mpereira/tty-solitaire"
    url = ""  # CI fills this

    package_type = "application"

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

    def _ncurses_flags(self):
        dep = self.dependencies["ncurses"]
        cflags = " ".join(f"-I{inc}" for inc in dep.cpp_info.includedirs)
        cflags += " -W -Wall -pedantic -std=c99 -DNCURSES_WIDECHAR"
        # Makefile 用 -DVERSION=\"1.4.1\" 注入版本字符串，需经 shell 后
        # 保留 C 字符串引号（裸 1.4.1 会被当作浮点常量报错）
        cflags += ' -DVERSION=\\"1.4.1\\"'
        ldflags = " ".join(f"-L{lib}" for lib in dep.cpp_info.libdirs)
        ldflags += " -lncursesw"
        return cflags, ldflags

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang") if compilers else "clang"
        cflags, ldflags = self._ncurses_flags()
        # 上游 Makefile 无 configure；PREFIX 仅影响 install 路径
        self.run(
            f"make -j1 CC={cc} PREFIX=/usr "
            f"CFLAGS='{cflags}' LDFLAGS='{ldflags}'"
        )
        # 上游测试实际执行（tests/ttysolitaire_test，67 具名用例/115 断言）
        self.run(
            f"make test CC={cc} "
            f"CFLAGS='{cflags}' LDFLAGS='{ldflags}'"
        )

    def package(self):
        # PREFIX 留空：DESTDIR 直接落包根（bin/ttysolitaire），
        # STRIP=true 保持未 strip（OHOS MAC 拒绝 stripped 二进制）
        self.run(
            "make install PREFIX= DESTDIR={} STRIP=true".format(
                self.package_folder
            )
        )
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        # OHOS 静态 ncurses 内置 stale staging terminfo 路径，游戏运行期
        # 必须显式设置 TERMINFO 指向依赖包内 terminfo 数据库。此处尽力
        # 注入（仅当依赖路径可解析为绝对路径时）；test_package 端另有
        # 直接依赖 + 缓存扫描兜底，二者互不依赖。
        terminfo = ""
        dep = self.dependencies.get("ncurses")
        if dep:
            cands = []
            pkg = getattr(dep, "package_folder", None)
            if pkg:
                cands.append(os.path.join(pkg, "share", "terminfo"))
            for inc in (dep.cpp_info.includedirs or []):
                if os.path.isabs(inc):
                    cands.append(
                        os.path.join(os.path.dirname(inc), "share", "terminfo")
                    )
            for cand in cands:
                if cand and os.path.isdir(cand):
                    terminfo = cand
                    break
        if terminfo:
            self.buildenv_info.define_path("TERMINFO", terminfo)
            self.runenv_info.define_path("TERMINFO", terminfo)
