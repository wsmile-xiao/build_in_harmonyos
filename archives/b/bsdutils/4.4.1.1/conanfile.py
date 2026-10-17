#!/usr/bin/env python3
"""Conan recipe for bsdutils 4.4.1.1 — Debian slink BSD 工具集.

bsdutils 4.4.1.1 是 Debian slink（Debian 2.1，1999）的 BSD 工具集源码包
（kill/logger/renice/script/wall/chroot + err/getopt/ttymsg 公共源码），
.old-style POSIX make 构建（Makefile 硬编码 CC=gcc——命令行覆盖 CC=clang）。

Upstream: Debian snapshot 官方归档（debian-archive slink source/base），
版本 4.4.1.1 即 Debian bsdutils 老版最高版本。

Build:  make -j1（CC=clang CFLAGS 保留 -DDEBIAN，-lutil 保留——musl
        libutil.a 为兼容空库，openpty/login_tty 由 musl libc 提供）。
Install: bin/kill + bin/{logger,renice,script,wall} + bin/chroot。
Type:   application（CLI 工具——commands.json 软件级声明）

Deps:   仅 -lutil（musl 兼容空库）——无 Conan 依赖。

R26: Not applicable（无系统名冲突）。
R32: settings.os 需检查 ("Linux", "OHOS")。
R38: CLI 工具——commands.json 已声明（软件级 archives/b/bsdutils/commands.json）。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


class BsdutilsConan(ConanFile):
    name = "bsdutils"
    version = "4.4.1.1"
    description = "Debian slink BSD 工具集（kill/logger/renice/script/wall/chroot）"
    license = "BSD-3-Clause"
    homepage = "https://packages.debian.org/source/bsdutils"
    url = "https://snapshot.debian.org/package/bsdutils/4.4.1.1/"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        from conan.tools.files import export_conandata_patches
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        from conan.tools.files import apply_conandata_patches
        apply_conandata_patches(self)

        # Makefile 硬编码 CC=gcc、LDFLAGS=-s——命令行覆盖为 clang；
        # -lutil 保留（musl libutil.a 兼容空库，openpty/login_tty 由
        # musl libc 提供——script.c 的 openpty/login_tty 链接正常）。
        # 另：Makefile 的 all: 不含 chroot（其规则被注释）——patch
        # 启用 chroot 构建（chroot.o + err.o + getopt.o）。
        mf = os.path.join(self.source_folder, "Makefile")
        with open(mf, "r", encoding="utf-8") as f:
            m = f.read()
        m = m.replace("all: $(BINPROGS) $(USRBINPROGS) $(SGIDTTYPROGS)",
                      "all: $(BINPROGS) $(USRBINPROGS) $(SGIDTTYPROGS) chroot")
        m = m.replace("#chroot:   chroot.o err.o getopt.o",
                      "chroot:   chroot.o err.o getopt.o")
        with open(mf, "w", encoding="utf-8") as f:
            f.write(m)
        # getopt.c 用 BSD rindex（strrchr 别名）——musl libc.a 虽有
        # rindex.o 但链接行为不稳（-D_GNU_SOURCE 后仍 undefined）——
        # 直接替换为 POSIX strrchr（语义相同，一劳永逸）。
        g = os.path.join(self.source_folder, "getopt.c")
        with open(g, "r", encoding="utf-8") as f:
            s = f.read()
        s = s.replace("rindex(", "strrchr(")
        with open(g, "w", encoding="utf-8") as f:
            f.write(s)

        # renice.c 老代码 `extern int errno;`——musl 的 errno 是
        # __errno_location() 宏（线程局部），显式声明导致链接找不到
        # errno 符号——移除声明并补 #include <errno.h>。
        g = os.path.join(self.source_folder, "renice.c")
        with open(g, "r", encoding="utf-8") as f:
            s = f.read()
        s = s.replace("\textern int errno;\n", "")
        if "#include <errno.h>" not in s:
            s = s.replace("#include <stdio.h>", "#include <stdio.h>\n#include <errno.h>", 1)
        with open(g, "w", encoding="utf-8") as f:
            f.write(s)

        # script.c `#if !defined(__GLIBC__) #include <tzfile.h> #endif`——
        # tzfile.h 是 glibc 私有头，musl 无此头（OHOS 非 glibc 会命中
        # include 分支且文件不存在）——且 script.c 未实际使用 tz 功能，
        # 禁用该 include 块。
        g = os.path.join(self.source_folder, "script.c")
        with open(g, "r", encoding="utf-8") as f:
            s = f.read()
        s = s.replace("#if !defined(__GLIBC__)\n#include <tzfile.h>\n#endif /* __GLIBC__ */",
                      "/* tzfile.h: glibc 私有头——musl 无且未实际使用 tz 功能 */")
        # script.c 用 BSD 老式 `union wait status`（musl 无此类型）——
        # 改 int status（wait3 调用本就强转 (int *)&status）。
        s = s.replace("union wait status;", "int status;")
        s = s.replace("wait3((int *)&status, WNOHANG, 0)", "wait3(&status, WNOHANG, 0)")
        with open(g, "w", encoding="utf-8") as f:
            f.write(s)

        # wall.c：①缺 <time.h>（struct tm 不完整、localtime 赋值报错）
        # ②用 BSD 类型 u_int（musl 无——E113 同款，替换 unsigned int）。
        g = os.path.join(self.source_folder, "wall.c")
        with open(g, "r", encoding="utf-8") as f:
            s = f.read()
        if "#include <time.h>" not in s:
            s = s.replace("#include <sys/time.h>", "#include <sys/time.h>\n#include <time.h>", 1)
        s = s.replace("(u_int)", "(unsigned int)")
        with open(g, "w", encoding="utf-8") as f:
            f.write(s)

        # ttymsg.c 用 glibc 私有宏 MAXNAMLEN（musl 无——boa 同款，
        # DRAFT-ohos-musl-no-maxnamlen 覆盖）——替换 NAME_MAX 并补
        # <limits.h>（musl 的 NAME_MAX 定义于此）。
        g = os.path.join(self.source_folder, "ttymsg.c")
        with open(g, "r", encoding="utf-8") as f:
            s = f.read()
        s = s.replace("MAXNAMLEN", "NAME_MAX")
        if "#include <limits.h>" not in s:
            s = s.replace("#include <dirent.h>", "#include <dirent.h>\n#include <limits.h>", 1)
        with open(g, "w", encoding="utf-8") as f:
            f.write(s)

        # ttymsg.c 用 BSD 老式 sigsetmask(0)（fork 子进程恢复信号掩码——
        # musl 无此 API）——替换为 POSIX sigprocmask 等价物
        # （sigemptyset + SIG_SETMASK 空掩码）。
        g = os.path.join(self.source_folder, "ttymsg.c")
        with open(g, "r", encoding="utf-8") as f:
            s = f.read()
        s = s.replace(
            "\t\t\t(void) sigsetmask(0);",
            "\t\t\t{ sigset_t _sm; sigemptyset(&_sm); (void) sigprocmask(SIG_SETMASK, &_sm, NULL); }")
        with open(g, "w", encoding="utf-8") as f:
            f.write(s)

        # __P() K&R 原型宏（logger/kill/script/wall/chroot + err.h 均用）
        # 源码未 include <sys/cdefs.h>——用 clang -include 强制预包含
        # musl 的 sys/cdefs.h（其中定义 __P(protos) protos），避免
        # -D'__P(protos)=protos' 的括号触发 shell 语法错误。
        cmd = ('make -j1 CC=clang '
               'CFLAGS="-O2 -I. -DDEBIAN -Wno-deprecated-non-prototype '
               '-include sys/cdefs.h" '
               'LDFLAGS=""')
        self.run(cmd, cwd=self.source_folder, env="conanrun")

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        for prog in ("kill", "logger", "renice", "script", "wall", "chroot"):
            copy(self, prog, src=self.source_folder, dst=bindir)

    def package_info(self):
        self.output.info("bsdutils 4.4.1.1: bin/kill bin/logger bin/renice bin/script bin/wall bin/chroot")
        # R38 — CLI 工具
        self.conf_info.define("user.tools.bsdutils:exe", "kill")
