#!/usr/bin/env python3
"""Conan recipe for bsdmainutils 12.1.8 — Debian 维护的 FreeBSD 工具集。

bsdmainutils 是 Debian 维护的 FreeBSD 工具集（12.1.3 后主包变
transitional——usr.bin 仅剩 calendar + ncal，col/column/hexdump 等已迁
util-linux）。.POSIX make 构建（顶层 Makefile 递归 usr.bin/*）。

依赖处理（关键）：
- ncurses/6.6（ncal 的 -ltinfo——制品仓已发布）
- libbsd（calendar/ncal 的 -lbsd）：主仓库无 conanfile.py、制品仓无
  libbsd 包——仿 afsctool 先例**绕过**：移除 -lbsd 链接与
  -include bsd/*.h；strtonum（musl 无）内置 OpenBSD 兼容实现；
  arc4random_uniform musl 自带（stdlib.h 实测可链接）；
  login_cap.h 仅 include 未调用（移除 include）。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class BsdmainutilsConan(ConanFile):
    name = "bsdmainutils"
    version = "12.1.8"
    description = "Debian-maintained FreeBSD utilities (calendar, ncal)"
    license = "BSD-3-Clause"
    homepage = "https://salsa.debian.org/meskes/bsdmainutils"
    url = ""
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        # ncurses（ncal 的 -ltinfo）——制品仓已发布；
        # libbsd 绕过（无制品仓包）——配方内内置 strtonum 兼容实现
        self.requires("ncurses/6.6")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("bsdmainutils is supported only on Linux/OHOS")

    def layout(self):
        basic_layout(self)

    def source(self):
        # Debian 源包无独立 orig——bsdmainutils_12.1.8.tar.xz 直接是源码树
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # PkgConfigDeps 生成 ncursesw.pc——ncal 的 -ltinfo 需要
        deps = PkgConfigDeps(self)
        deps.generate()

    def build(self):
        # ---------- patch：绕过 libbsd（仿 afsctool 先例） ----------
        # 1) calendar/Makefile：移除 -lbsd 链接与 -include bsd/stdlib.h
        cm = os.path.join(self.source_folder, "usr.bin", "calendar", "Makefile")
        if os.path.isfile(cm):
            with open(cm, encoding="utf-8") as f:
                s = f.read()
            s = s.replace("LIBS = -lbsd\n", "LIBS =\n")
            s = s.replace("FLAGS = -include sys/uio.h -include bsd/stdlib.h\n",
                          "FLAGS = -include sys/uio.h\n")
            with open(cm, "w", encoding="utf-8") as f:
                f.write(s)
        # 2) ncal/Makefile：移除 -lbsd 与 -ltinfo（tgetent/tgetstr 已
        #    stub——ncurses 制品无 libtinfo，ncal 无其他 termcap 符号）
        #    + bsd/string.h include
        nm = os.path.join(self.source_folder, "usr.bin", "ncal", "Makefile")
        if os.path.isfile(nm):
            with open(nm, encoding="utf-8") as f:
                s = f.read()
            s = s.replace("FLAGS  = -D_GNU_SOURCE -include bsd/string.h\n",
                          "FLAGS  = -D_GNU_SOURCE\n")
            s = s.replace("LIBS  += -ltinfo -lbsd\n", "LIBS  +=\n")
            with open(nm, "w", encoding="utf-8") as f:
                f.write(s)
        # 3) calendar.c：移除 <login_cap.h>（仅 include 未调用任何 login_* 函数）
        cc = os.path.join(self.source_folder, "usr.bin", "calendar", "calendar.c")
        if os.path.isfile(cc):
            with open(cc, encoding="utf-8") as f:
                s = f.read()
            s = s.replace("#include <login_cap.h>\n", "")
            # pledge：OpenBSD 沙箱承诺调用——musl（OHOS）无此函数，stub 为 0
            # （if (0 == -1) 恒假——不进入 err 分支，合法 C 编译通过）
            import re
            s = re.sub(r'pledge\("[^"]*", NULL\)', '0', s)
            # setusercontext：login_cap 库函数（LOGIN_SETALL/LOGIN_SETLOGIN
            # 宏来自 login_cap.h）——musl 无——替换为等价的 setuid 调用
            # （doall 模式 fork 子进程后按用户 uid 切换，Linux 语义一致）
            s = re.sub(
                r'setusercontext\(NULL, pw, pw->pw_uid,\s*LOGIN_SETALL \^ LOGIN_SETLOGIN\)',
                'setuid(pw->pw_uid)', s)
            with open(cc, "w", encoding="utf-8") as f:
                f.write(s)
        # 4) 内置 strtonum 兼容实现（musl 无 strtonum）——OpenBSD 语义，
        #    写入 usr.bin/calendar/compat_strtonum.c 并追加到 SRC
        compat = os.path.join(self.source_folder, "usr.bin", "calendar",
                              "compat_strtonum.c")
        with open(compat, "w", encoding="utf-8") as f:
            f.write(STRTONUM_COMPAT)
        if os.path.isfile(cm):
            with open(cm, encoding="utf-8") as f:
                s = f.read()
            s = s.replace("SRC  = calendar.c io.c day.c ostern.c paskha.c pesach.c\n",
                          "SRC  = calendar.c io.c day.c ostern.c paskha.c pesach.c compat_strtonum.c\n")
            with open(cm, "w", encoding="utf-8") as f:
                f.write(s)
        # 5) calendar.h：`extern u_long julian`——u_long 是 BSD 旧类型名
        #    （musl 无），改为 unsigned long；paskha.c 等仅 include
        #    stdio.h + calendar.h——musl 下 time_t 未定义（FreeBSD 由
        #    sys/types.h 链式带入），补 #include <time.h>
        ch = os.path.join(self.source_folder, "usr.bin", "calendar", "calendar.h")
        if os.path.isfile(ch):
            with open(ch, encoding="utf-8") as f:
                s = f.read()
            s = s.replace("extern u_long julian;", "extern unsigned long julian;")
            s = s.replace("extern struct passwd *pw;",
                          "#include <time.h>\n\nextern struct passwd *pw;")
            with open(ch, "w", encoding="utf-8") as f:
                f.write(s)
        # 6) ncal：编译错修复——
        #    a) __FBSDID 宏（musl sys/cdefs.h 无）→ 移除该行
        #    b) `#include <calendar.h>` 尖括号找不到同目录头 → 改引号
        #    c) `#include <term.h>`（ncurses 头，OHOS 无 tty——isatty 恒假
        #       不会走到 tgetent/tgetstr）→ 移除 include + 移除 termcap
        #       高亮初始化块（term_so/term_se 保持 NULL——高亮不生效）
        #    d) D_MD_ORDER（musl langinfo.h 无此 FreeBSD 扩展宏）→ 固定
        #       m/d 日期顺序（d_first=0——C locale 默认）
        import re as _re
        for fname in ("ncal.c", "calendar.c", "easter.c"):
            p = os.path.join(self.source_folder, "usr.bin", "ncal", fname)
            if not os.path.isfile(p):
                continue
            with open(p, encoding="utf-8") as f:
                s = f.read()
            s = _re.sub(r'__FBSDID\("[^"]*"\);\n', '', s)
            s = s.replace('#include <calendar.h>', '#include "calendar.h"')
            s = s.replace('#include <term.h>\n', '')
            with open(p, "w", encoding="utf-8") as f:
                f.write(s)
        # ncal.c 专属：D_MD_ORDER + termcap 高亮块（仅 ncal.c 有）
        p = os.path.join(self.source_folder, "usr.bin", "ncal", "ncal.c")
        if os.path.isfile(p):
            with open(p, encoding="utf-8") as f:
                s = f.read()
            s = s.replace("d_first = (*nl_langinfo(D_MD_ORDER) == 'd');",
                          "d_first = 0; /* musl 无 D_MD_ORDER——固定 m/d 顺序 */")
            s = s.replace("""		if (isatty(STDOUT_FILENO) && tgetent(tbuf, NULL) == 1) {
			b = cbuf;
			term_so = tgetstr("so", &b);
			term_se = tgetstr("se", &b);
		}""",
                          """		/* OHOS 无 tty（isatty 恒假）——termcap 高亮不生效，
		 * term_so/term_se 保持 NULL。 */""")
            with open(p, "w", encoding="utf-8") as f:
                f.write(s)

        # ---------- 构建 ----------
        # OHOS 无 cc（Makefile 默认 CC=cc）——内联 CC=clang；PkgConfigDeps
        # 生成的 ncursesw.pc 在 generators_folder——PKG_CONFIG_PATH 指向它。
        # 注意：conan run() 的 env 参数是 list（非 dict）——环境变量内联进命令
        # -j1 绕 OHOS 沙箱禁 mkfifo（make jobserver）
        cmd = ("export CC=clang CFLAGS=\"-O2 -g \" "
               "PKG_CONFIG_PATH=\"%s:$PKG_CONFIG_PATH\"; make -j1"
               % self.generators_folder)
        self.run(cmd, cwd=self.source_folder, env="conanrun")

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        copy(self, "calendar", src=os.path.join(self.source_folder, "usr.bin", "calendar"),
             dst=bin_dir, keep_path=False)
        copy(self, "ncal", src=os.path.join(self.source_folder, "usr.bin", "ncal"),
             dst=bin_dir, keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []


# OpenBSD strtonum 兼容实现（musl libc 无此函数——bsdmainutils 的
# calendar/io.c 用到）。语义与 OpenBSD 一致：解析十进制长整数，
# 越界/非法时经 errstrp 返回错误描述并返回 0。
STRTONUM_COMPAT = r'''/*
 * strtonum compatibility implementation for musl (OHOS).
 * OpenBSD semantics: parse decimal long long; on error set *errstrp
 * to "invalid" / "too small" / "too large" and return 0.
 */
#include <errno.h>
#include <limits.h>
#include <stdlib.h>

#define STRTONUM_INVALID   1
#define STRTONUM_TOOSMALL  2
#define STRTONUM_TOOLARGE  3

long long
strtonum(const char *numstr, long long minval, long long maxval,
         const char **errstrp)
{
    long long ll = 0;
    char *ep;
    int error = 0;
    struct errval {
        const char *errstr;
        int err;
    } ev[4] = {
        { NULL, 0 },
        { "invalid", EINVAL },
        { "too small", ERANGE },
        { "too large", ERANGE },
    };

    ev[0].err = errno;
    errno = 0;
    if (minval > maxval) {
        error = STRTONUM_INVALID;
    } else {
        ll = strtoll(numstr, &ep, 10);
        if (numstr == ep || *ep != '\0')
            error = STRTONUM_INVALID;
        else if ((ll == LLONG_MIN && errno == ERANGE) || ll < minval)
            error = STRTONUM_TOOSMALL;
        else if ((ll == LLONG_MAX && errno == ERANGE) || ll > maxval)
            error = STRTONUM_TOOLARGE;
    }
    if (errstrp != NULL)
        *errstrp = ev[error].errstr;
    errno = ev[error].err;
    if (error)
        return (0);
    return (ll);
}
'''
