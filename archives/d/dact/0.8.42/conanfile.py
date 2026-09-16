#!/usr/bin/env python3
"""Conan recipe for dact 0.8.42 — 多算法分块压缩工具（Roy Keene）。

上游是 autotools 项目（39 个 C 文件），产出 `dact` 与 `libdact.a/.so`。
本配方直接驱动 OHOS clang 复刻其 **static 构建模式**，要点与取舍：

1. **不跑 autotools configure**：上游 configure.in 用自定义 m4 宏
   `DC_CHK_MODULE(z, comp_zlib.c comp_mzlib.c comp_mzlib2.c, HAVE_LIBZ)` 探测
   （内部是 `AC_CHECK_LIB(<lib>, main, ...)` 的"能链接即算有"惯用写法），并把命中的
   源文件列表拼进 `ALGO`、库名拼进 `MODLIBS`。直编时按同样的规则显式给出 ALGO 即可。
2. **`HAVE_CONFIG_H` 必须定义**：`dact.h` 的写法是
   `#ifdef HAVE_CONFIG_H / #include "config.h" / #endif` —— 不定义该宏，生成的
   config.h **根本不会被包含**，全部能力宏形同虚设。
3. **能力宏与算法表必须自洽**：`algorithms.h` 是一张**位置敏感**的函数指针表，
   每个条目按 `#ifdef HAVE_LIBZ / HAVE_LIBBZ2 / DEBUG` 切换成真实实现或
   `DACT_FAILED_ALGO`。因此"定义了哪个宏"就必须"链接了哪个 .c"，否则要么
   表里引用未定义符号、要么把可用算法错误地注册成失败占位。
   本次开启 zlib（制品仓 `zlib/1.3.1`），不开启 bz2/lzo/mcrypt（对应 .c 不编译）。
4. **lzo 系列无需编译**：`comp_lzoox/lzooy/lzota.h` 在
   `(defined(USE_MODULES) && !defined(AS_MODULE)) || !defined(HAVE_LIBLZO) || ...`
   时把 `comp_lzoX_algo` 宏定义为 `DACT_FAILED_ALGO`，故未启用时是编译期别名，不产生符号。
5. **不启用动态模块**（`USE_MODULES`）：模块模式依赖 `dlopen` 与 `module_dir`，
   在 OHOS 沙箱下无必要；static 模式把算法直接链进主程序，产物自包含。
6. `DACT_CONFIG_FILE` / `EXEEXT` 原由 Makefile 以 `-D...=\"...\"` 注入，
   本配方写进生成的 config.h，避开跨 shell 引号转义。
"""
import json
import os

from conan import ConanFile
from conan.tools.files import copy, get

# 上游 Makefile.in 的核心对象（OBJS）
CORE_OBJS = ["dact_common", "comp_fail", "comp_plain", "buffer", "header", "sort",
             "dact", "module", "parse", "dendian", "crc", "net", "ui", "sfx",
             "libdact",
             # 上游 configure.in 的 AC_REPLACE_FUNCS(getopt strsep getpass mkstemp uname)：
             # libc 缺哪个就编自带的哪个。OHOS musl 的 <unistd.h> **完全没有 getpass
             # 声明**（glibc 会声明，musl 只在 _GNU_SOURCE 下才有），故必须使用自带实现；
             # getopt/strsep/mkstemp/uname 由 musl 提供，对应自带 .c 不编译。
             "getpass"]
# 上游 Makefile.in 的 ALGO 内置部分 + zlib 模块（DC_CHK_MODULE(z, ...) 命中后追加）
ALGO_OBJS = ["comp_snibble", "comp_delta", "comp_text", "comp_rle",
             "cipher_chaos", "cipher_sub", "cipher_psub",
             # zlib 模块（HAVE_LIBZ）
             "comp_zlib", "comp_mzlib", "comp_mzlib2"]

CONFIG_H = """\
/* config.h — dact 0.8.42 由 conan recipe 生成（上游由 autoconf 从 config.h.in 产出）。
 *
 * 注意：dact.h 的写法是 `#ifdef HAVE_CONFIG_H / #include "config.h" / #endif`，
 * 因此编译时必须同时传 -DHAVE_CONFIG_H，否则本文件不会被包含、下列宏全部失效。
 *
 * 本文件只定义 OHOS(musl) 上确实存在的能力；未定义 = 关闭对应可选特性。
 * 与 algorithms.h 的位置敏感算法表配套：定义了 HAVE_LIBZ 就必须链接
 * comp_zlib/comp_mzlib/comp_mzlib2（recipe 的 ALGO_OBJS 已对应）。
 */
#define HAVE_CONFIG_H 1

/* ── 头文件能力（OHOS musl 全部具备） ── */
#define HAVE_ARPA_INET_H 1
#define HAVE_DIRENT_H 1
#define HAVE_DLFCN_H 1
#define HAVE_ERRNO_H 1
#define HAVE_FCNTL_H 1
#define HAVE_GETOPT_H 1
#define HAVE_INTTYPES_H 1
#define HAVE_NETDB_H 1
#define HAVE_NETINET_IN_H 1
#define HAVE_STDARG_H 1
#define HAVE_STDINT_H 1
#define HAVE_STDIO_H 1
#define HAVE_STDLIB_H 1
#define HAVE_STRING_H 1
#define HAVE_STRINGS_H 1
#define HAVE_SYS_SOCKET_H 1
#define HAVE_SYS_STAT_H 1
#define HAVE_SYS_TIME_H 1
#define HAVE_SYS_TYPES_H 1
#define HAVE_SYS_UTSNAME_H 1
#define HAVE_SYS_WAIT_H 1
#define HAVE_UNISTD_H 1
#define HAVE_ZLIB_H 1

/* ── 函数/设施能力 ── */
#define HAVE_DEV_URANDOM 1
#define HAVE_GETHOSTBYNAME 1
#define HAVE_INET_ADDR 1
#define HAVE_INET_ATON 1
#define HAVE_MKSTEMP 1
#define HAVE_SOCKET 1
#define HAVE_STRSEP 1
#define HAVE_UNAME 1
#define HAVE_LRAND48 1
#define HAVE_SRAND48 1
/* ★ 刻意不定义 HAVE_GETPASS —— OHOS musl 的 <unistd.h> 不声明 getpass，
 *   且 dact.h 的约定是 `#ifndef HAVE_GETPASS / #include "getpass.h"`，
 *   因此这里留空即启用上游自带的 getpass.c（已加入 recipe 的 CORE_OBJS）。 */
/* #undef HAVE_GETPASS */

/* ── zlib 模块（DC_CHK_MODULE(z, ...) 命中） ── */
#define HAVE_LIBZ 1
#define HAVE_COMPRESS2 1
#define HAVE_GZDOPEN 1

/* ── 未启用的可选模块（保持未定义） ── */
/* #undef HAVE_LIBBZ2 */
/* #undef HAVE_BZLIB_H */
/* #undef HAVE_LIBLZO */
/* #undef HAVE_LZO1X_H */
/* #undef HAVE_LZO1Y_H */
/* #undef HAVE_LZO2A_H */
/* #undef HAVE_LZOCONF_H */
/* #undef HAVE_LIBMCRYPT */
/* #undef HAVE_MCRYPT_H */
/* #undef HAVE_LIBINTL_H */
/* #undef CHECK_VERSION */
/* #undef DEBUG */
/* #undef USE_MODULES */
/* #undef DACT_DEBIAN_UPGRADE_PROC */
/* #undef HAVE_WINDOWS_H */
/* #undef HAVE_WINDOWSX_H */
/* #undef HAVE_WINSOCK2_H */
/* #undef HAVE_WINSVC_H */
/* #undef HAVE_LIBWSOCK32 */

/* 上游 Makefile 以 -D 注入的字符串宏（放这里避开跨 shell 引号转义） */
#ifndef DACT_CONFIG_FILE
#define DACT_CONFIG_FILE "/usr/local/etc/dact.conf"
#endif
#ifndef EXEEXT
#define EXEEXT ""
#endif
"""


class DactConan(ConanFile):
    name = "dact"
    version = "0.8.42"
    description = "Dynamic Adaptive Compression Tool (multi-algorithm block compressor)"
    license = "GPL-2.0-or-later"
    homepage = "https://www.rkeene.org/oss/dact/"
    topics = ("compression", "cli", "algorithm", "zlib")
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"
    requires = "zlib/1.3.1"

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
        src = self.source_folder
        with open(os.path.join(src, "config.h"), "w", encoding="utf-8") as f:
            f.write(CONFIG_H)

        z = self.dependencies["zlib"].cpp_info
        inc = " ".join(f'-I{d.replace(os.sep, "/")}' for d in z.includedirs)
        lib = " ".join(f'-L{d.replace(os.sep, "/")}' for d in z.libdirs)

        # 上游 CFLAGS：-DDACT_CONFIG_FILE / -DEXEEXT 已移入 config.h；
        # -DHAVE_CONFIG_H 必须传（dact.h 用它决定是否包含 config.h）。
        cflags = (os.environ.get("CFLAGS", "")
                  + " -O2 -Wall -DHAVE_CONFIG_H -I."
                  + " -Wno-unused-parameter -Wno-unused-function -Wno-format-truncation")
        objs = CORE_OBJS + ALGO_OBJS
        for o in objs:
            self.run(f'cd {src} && {cc} {cflags} {inc} -c {o}.c -o {o}.o')
        allobj = " ".join(f"{o}.o" for o in objs)
        self.run(f'cd {src} && {cc} {cflags} {allobj} {lib} -lz -o dact')

        # 上游 Makefile 会生成 dact.conf（运行时配置，module_dir 指向 datadir）
        conf_path = os.path.join(src, "dact.conf")
        with open(conf_path, "w", encoding="utf-8") as f:
            f.write("version_check    off\n"
                    "#block_size      0\n"
                    "#exclude_algo    0\n"
                    "use_urls         off\n"
                    "color_ui         off\n"
                    "network_access   off\n"
                    "binary_check     off\n"
                    "module_dir       /usr/local/share/dact\n")

    def package(self):
        bin_dst = os.path.join(self.package_folder, "bin")
        doc_dst = os.path.join(self.package_folder, "share", "doc", "dact")
        etc_dst = os.path.join(self.package_folder, "etc")
        man_dst = os.path.join(self.package_folder, "share", "man", "man1")
        copy(self, "dact", src=self.source_folder, dst=bin_dst)
        copy(self, "dact.conf", src=self.source_folder, dst=etc_dst)
        copy(self, "Docs/*", src=self.source_folder, dst=doc_dst)
        copy(self, "AUTHORS", src=self.source_folder, dst=doc_dst)
        copy(self, "ChangeLog", src=self.source_folder, dst=doc_dst)
        p = os.path.join(bin_dst, "dact")
        if os.path.isfile(p):
            os.chmod(p, 0o755)
