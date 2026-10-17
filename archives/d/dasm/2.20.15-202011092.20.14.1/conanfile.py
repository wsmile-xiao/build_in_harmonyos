#!/usr/bin/env python3
"""Conan recipe for dasm — the DASM macro assembler (8-bit cross assembler).

上游是 1988 年起的老项目（Matthew Dillon 起源），构建极简：`src/` 下 11 个 .c
直接链接成 `dasm`，外加单文件工具 `ftohex`。本配方不跑上游 Makefile，直接驱动
OHOS clang，原因与要点：

1. **上游 Makefile 不可直接用于跨编译**：`src/Makefile` 用 `$(CC)` 但**不透明地**
   依赖 make 隐式规则完成 `ftohex.o → ftohex` 的链接，且顶层 `build` 目标会
   `mkdir -p bin && cp src/dasm bin/dasm` —— 在 conan 的 build/source 分离布局里
   会往源码树写产物。直编可完全避开这些副作用。
2. ★ **OHOS musl 没有 `strlcat`**：`errors.c` 无条件调用 `strlcat()`
   （append_level / append_location / append_information 三处）。`strlcat`/`strlcpy`
   源自 OpenBSD，**glibc 直到 2.38（2023-08）才纳入**，Debian 能编过正是靠这一点；
   musl 至今未提供。在 musl 上表现为 C99 隐式函数声明（clang 15+ 默认按错误处理）
   或链接期 `undefined reference to 'strlcat'`。本配方用一个前置包含的兼容头 +
   单独编译的兼容实现补桥（OpenBSD 语义），**不改上游源码、不删调用**。
3. **`-include` 而非改源码**：兼容头通过 `-include` 注入到每个编译单元之前，
   因此在 `<string.h>` 声明 `strlcat` 的 libc 上也只是把该声明宏改名为我们自己的
   符号，签名一致、无双定义风险；在 musl 上则同时提供声明与实现。
4. **不定义 `-DHAVE_*`**：本项目没有 config.h / autoconf，能力完全由源码硬编码，
   无能力宏自洽问题。
"""
import json
import os

from conan import ConanFile
from conan.tools.files import copy, get

# 上游 src/Makefile 的 OBJS（顺序一致，便于与上游对照）
CORE_SRCS = ["main", "ops", "globals", "exp", "symbols",
             "mne6303", "mne6502", "mne68705", "mne6811", "mnef8", "mne68908"]

# ── OHOS/musl 缺失的 strlcat/strlcpy 补桥（OpenBSD 语义）────────────────────
COMPAT_H = """\
/* dasm_ohos_compat.h — OHOS(musl) 缺失的 strlcat/strlcpy 补桥。
 *
 * 由 conan recipe 在 build 前生成，经 -include 前置到每个编译单元。
 * strlcat/strlcpy 源自 OpenBSD：glibc 2.38+ 才有，musl 至今没有。
 * dasm 的 errors.c 无条件调用 strlcat()，故必须在 musl 上补齐。
 *
 * 用宏改名而不是条件声明：在已提供 strlcat 的 libc 上，<string.h> 里的
 * 原型会被一并改名成同签名的自带实现，不会产生重复定义。
 */
#ifndef DASM_OHOS_COMPAT_H
#define DASM_OHOS_COMPAT_H

#include <stddef.h>

size_t dasm_compat_strlcat(char *dst, const char *src, size_t siz);
size_t dasm_compat_strlcpy(char *dst, const char *src, size_t siz);

#define strlcat dasm_compat_strlcat
#define strlcpy dasm_compat_strlcpy

#endif /* DASM_OHOS_COMPAT_H */
"""

COMPAT_C = """\
/* dasm_ohos_compat.c — OpenBSD strlcat/strlcpy 语义实现（musl 补桥）。
 * dasm 用到的是 strlcat 的"返回拼接后总长（截断时为所需的完整长度）"语义：
 * errors.c 把该返回值当作已写长度继续推进，故必须严格复刻而不是简单 strncat。
 */
#include <string.h>
#include <stddef.h>

size_t dasm_compat_strlcpy(char *dst, const char *src, size_t siz)
{
    const char *s = src;
    size_t n = siz;

    if (n != 0) {
        while (--n != 0) {
            if ((*dst++ = *s++) == '\\0') {
                break;
            }
        }
    }
    if (n == 0) {
        if (siz != 0) {
            *dst = '\\0';
        }
        while (*s++)
            ;
    }
    return (size_t)(s - src - 1);
}

size_t dasm_compat_strlcat(char *dst, const char *src, size_t siz)
{
    char *d = dst;
    const char *s = src;
    size_t n = siz;
    size_t dlen;

    while (n-- != 0 && *d != '\\0') {
        d++;
    }
    dlen = (size_t)(d - dst);
    n = siz - dlen;

    if (n == 0) {
        return dlen + strlen(s);
    }
    while (*s != '\\0') {
        if (n != 1) {
            *d++ = *s;
            n--;
        }
        s++;
    }
    *d = '\\0';
    return dlen + (size_t)(s - src);
}
"""


class DasmConan(ConanFile):
    name = "dasm"
    version = "2.20.15-202011092.20.14.1"
    description = "DASM macro assembler — cross assembler for 6502/6803/68HC11/68705/68908/F8"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/dasm-assembler/dasm"
    topics = ("assembler", "cross-assembler", "6502", "atari2600", "retro", "toolchain")
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _cc(self):
        """解析 C 编译器：conf > CC 环境变量 > 裸 clang（R33：不在 self.run 里做 shell 展开）。"""
        compilers = self.conf.get("tools.build:compiler_executables")
        if isinstance(compilers, str):
            try:
                compilers = json.loads(compilers)
            except ValueError:
                compilers = None
        if isinstance(compilers, dict) and compilers.get("c"):
            return compilers["c"]
        return os.environ.get("CC", "clang")

    def build(self):
        cc = self._cc()
        src = os.path.join(self.source_folder, "src")

        # 写入补桥（放源码树同级可被 -include 相对定位，但用绝对路径更稳）
        compat_h = os.path.join(src, "dasm_ohos_compat.h")
        compat_c = os.path.join(src, "dasm_ohos_compat.c")
        for path, text in ((compat_h, COMPAT_H), (compat_c, COMPAT_C)):
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)

        # 上游默认 CFLAGS 为空；这里仅加 -O2（不加 -pedantic/-Wall，避免上游
        # 老代码在 clang 新版本下的告警噪声影响判读）。
        cflags = (os.environ.get("CFLAGS", "")
                  + " -O2 -std=c99 -I."
                  + ' -include "' + compat_h.replace(os.sep, "/") + '"')

        # 补桥实现（strlcat 出现在核心目标里）
        self.run(f'cd "{src}" && {cc} {cflags} -c dasm_ohos_compat.c -o dasm_ohos_compat.o')

        for s in CORE_SRCS:
            self.run(f'cd "{src}" && {cc} {cflags} -c {s}.c -o {s}.o')

        objs = " ".join(f"{s}.o" for s in CORE_SRCS) + " dasm_ohos_compat.o"
        self.run(f'cd "{src}" && {cc} {cflags} {objs} -o dasm')

        # ftohex：单文件工具，不依赖 strlcat，但仍统一走兼容头不影响结果
        self.run(f'cd "{src}" && {cc} {cflags} -c ftohex.c -o ftohex.o')
        self.run(f'cd "{src}" && {cc} {cflags} ftohex.o -o ftohex')

        # 产物归位到源码树根的 bin/（与上游顶层 Makefile 的布局一致）
        bindir = os.path.join(self.source_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        for name in ("dasm", "ftohex"):
            copy(self, name, src=src, dst=bindir)

    def package(self):
        bin_dst = os.path.join(self.package_folder, "bin")
        doc_dst = os.path.join(self.package_folder, "share", "doc", "dasm")
        man_dst = os.path.join(self.package_folder, "share", "man", "man1")
        mach_dst = os.path.join(self.package_folder, "share", "dasm", "machines")
        src = os.path.join(self.source_folder, "src")

        # ★ copy() 的 pattern 是拿**相对 src 的路径**做 fnmatch 的：
        #   必须以 <source>/src 作为 src，配 pattern "dasm" 才能命中 src/dasm。
        #   若用 source_folder 作 src，文件相对路径是 "bin/dasm"，
        #   fnmatch("bin/dasm", "dasm") 为假 —— 会静默一个字节都不拷（本包踩过）。
        copy(self, "dasm", src=src, dst=bin_dst)
        copy(self, "ftohex", src=src, dst=bin_dst)

        # 机器相关头文件（atari2600 的 vcs.h/macro.h 等，用户经 -I 引入；
        # channel-f 为 F8 汇编器配套）。Debian 包同样随包分发。
        copy(self, "*", src=os.path.join(self.source_folder, "machines"), dst=mach_dst)

        copy(self, "ChangeLog", src=self.source_folder, dst=doc_dst)
        copy(self, "NEWS", src=self.source_folder, dst=doc_dst)
        copy(self, "README", src=self.source_folder, dst=doc_dst)
        copy(self, "LICENSE", src=self.source_folder, dst=doc_dst)
        copy(self, "dasm.txt", src=os.path.join(self.source_folder, "docs"), dst=doc_dst)
        copy(self, "ftohex.txt", src=os.path.join(self.source_folder, "docs"), dst=doc_dst)
        copy(self, "dasm.1", src=os.path.join(self.source_folder, "docs"), dst=man_dst)

        for name in ("dasm", "ftohex"):
            p = os.path.join(bin_dst, name)
            if os.path.isfile(p):
                os.chmod(p, 0o755)
