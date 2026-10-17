#!/usr/bin/env python3
"""Conan recipe for uclibc 1.0.54 (uClibc-ng) — C 标准库（嵌入式）。

uClibc-ng 是独立的 C 标准库（glibc/musl 的替代品）。与普通三方库不同，它不是
链接在其他 libc 之上的库，而是自己提供 libc.so/libc.a、crt 启动文件、动态链接器
(ld-uClibc-*.so) 与整套 C 头文件。因此：

- 构建系统是 Kconfig + GNU make（类似 Linux 内核），不是 autotools/CMake。
- 上游不提供 `make check`；官方测试在独立仓库 uClibc-ng-test（不随 tarball 发布）。
- aarch64 无预置 defconfig（extra/Configs/defconfigs/ 下没有 aarch64），
  需用 KCONFIG_ALLCONFIG 片段 + allnoconfig 生成 .config（与 buildroot 相同方式）。
- 产物会与 OHOS 系统 musl sysroot 冲突：消费者需以 -nostdinc/-nostdlib 方式把
  uClibc 当作替代 libc 使用，而不是普通 add-requires 链接。

本配方目标：用 CI 的 aarch64-linux-ohos clang 交叉/本机编译 uClibc-ng，
产出 libc 与头文件，供需要 uClibc 运行时的下游（嵌入式交叉工具链等）使用。

注意：本机（Windows）无 OHOS 交叉工具链与 Conan，未执行 conan create；
本配方为前置适配产物，需在真机 shadow CI 上做首次构建与配置细化。
"""
import os

from conan import ConanFile
from conan.tools.files import get
from conan.tools.layout import basic_layout


# 最小 aarch64 配置片段：在 allnoconfig 基线上开启关键项。
# 符号名均已在 extra/Configs/Config.in / Config.aarch64 中核对存在。
# 这是初始配置，首次 shadow CI 需按 `make oldconfig` 提示与产物完整性逐步细化。
_UCLIBC_AARCH64_CONFIG = """\
# Target architecture
TARGET_aarch64=y
CONFIG_AARCH64_PAGE_SIZE_4K=y
TARGET_ARCH="aarch64"
# Threading: NPTL（aarch64 仅支持 NPTL）
UCLIBC_HAS_THREADS=y
UCLIBC_HAS_THREADS_NATIVE=y
# Shared library + PIC
DOPIC=y
HAVE_SHARED=y
# 基础 C 库能力
UCLIBC_HAS_CTYPE_TABLES=y
UCLIBC_HAS_WCHAR=y
UCLIBC_HAS_LFS=y
MALLOC_STANDARD=y
UCLIBC_SUSV4_LEGACY=y
UCLIBC_HAS_STUBS=y
UCLIBC_HAS_CRYPT_IMPL=y
UCLIBC_HAS_IPV6=y
UCLIBC_HAS_STRING_GENERIC_OPT=y
# aarch64 用 dup3 替代 dup2，需启用 Linux 特定 syscall
UCLIBC_LINUX_SPECIFIC=y
# clock_gettime 在 REALTIME 与 ADVANCED_REALTIME 同时开启时会被重复归档进 libc_so.a，关闭后者
# UCLIBC_HAS_ADVANCED_REALTIME is not set
"""


class UclibcConan(ConanFile):
    name = "uclibc"
    version = "1.0.54"
    description = "uClibc-ng: a small C standard library for embedded Linux systems."
    license = "LGPL-2.1"
    homepage = "https://uclibc-ng.org/"
    topics = ("libc", "c-library", "embedded", "cross-toolchain")

    settings = "os", "compiler", "build_type", "arch"

    # 无 Conan 运行时/构建依赖：uClibc 自包含。
    # 内核头文件来自 OHOS SDK sysroot（由 CI profile / tools.build:sysroot 提供）。

    def layout(self):
        basic_layout(self)
        self.folders.build = "."  # uClibc 在源码树内构建（Kconfig 生成 .config）

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _toolchain(self):
        # R33: 编译器从 Conan conf 获取，禁止裸用 shell 环境变量。
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return {
            "cc": compilers.get("c", "clang") if compilers else "clang",
            "ar": compilers.get("ar", "llvm-ar") if compilers else "llvm-ar",
            "nm": compilers.get("nm", "llvm-nm") if compilers else "llvm-nm",
            "objdump": compilers.get("objdump", "llvm-objdump") if compilers else "llvm-objdump",
            "strip": compilers.get("strip", "llvm-strip") if compilers else "llvm-strip",
            "ld": compilers.get("ld", "ld.lld") if compilers else "ld.lld",
        }

    def build(self):
        tc = self._toolchain()
        # 探测 OHOS SDK sysroot：CI 的 clang wrapper 不自动注入 --target/--sysroot。
        # clang -print-resource-dir 形如 .../native/llvm/lib/clang/<ver>，上溯 4 级到 .../native，
        # sysroot 在 .../native/sysroot（含 usr/include/aarch64-linux-ohos 等 multilib 目录）。
        import subprocess
        try:
            res_dir = subprocess.run(
                [tc["cc"], "-print-resource-dir"], capture_output=True, text=True, timeout=30
            ).stdout.strip()
        except Exception:
            res_dir = ""
        if res_dir:
            native = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(res_dir))))
            sysroot = os.path.join(native, "sysroot")
        else:
            sysroot = os.environ.get("OHOS_SYSROOT", "/usr")
        target_flags = f"--target=aarch64-linux-ohos --sysroot={sysroot}"
        cc_full = f'{tc["cc"]} {target_flags}'
        # profile 只提供 c/cpp 编译器；ar/nm/objdump/ld 需用 OHOS llvm 绝对路径。
        # llvm-strip 不存在，用 llvm-objcopy 代替（等价于 strip）。
        if res_dir:
            llvm_bin = os.path.join(native, "llvm", "bin")
            tc["ar"] = os.path.join(llvm_bin, "llvm-ar")
            tc["nm"] = os.path.join(llvm_bin, "llvm-nm")
            tc["objdump"] = os.path.join(llvm_bin, "llvm-objdump")
            tc["ld"] = os.path.join(llvm_bin, "ld.lld")
            tc["strip"] = "/data/service/hnp/bin/strip"  # GNU strip 2.45；llvm-objcopy 对 relocation 命名符号过严

        config_file = os.path.join(self.build_folder, "uclibc-aarch64.config")
        with open(config_file, "w", encoding="utf-8") as f:
            f.write(_UCLIBC_AARCH64_CONFIG)

        # 可写临时目录：/tmp 在鸿蒙 PC 只读，Kconfig 宿主工具与编译器需要。
        tmpdir = os.path.join(self.build_folder, ".tmp")
        os.makedirs(tmpdir, exist_ok=True)

        # HMDFS 上源码脚本无 other 执行位（owner 是解包 uid，运行用户无执行权限），
        # 直接执行会 Permission denied；改为显式 $(SHELL) 调用（与 gen_bits_syscall_h.sh 既有写法一致）。
        makefile_in = os.path.join(self.build_folder, "Makefile.in")
        with open(makefile_in, "r", encoding="utf-8") as f:
            mi = f.read()
        mi = mi.replace(
            "$(Q)$(top_srcdir)extra/scripts/conf-header.sh",
            "$(Q)$(SHELL) $(top_srcdir)extra/scripts/conf-header.sh",
        )
        mi = mi.replace(
            "$(shell $(top_srcdir)extra/scripts/relative_path.sh",
            "$(shell $(SHELL) $(top_srcdir)extra/scripts/relative_path.sh",
        )
        mi = mi.replace(
            "\t$(top_srcdir)extra/scripts/install_headers.sh",
            "\t$(SHELL) $(top_srcdir)extra/scripts/install_headers.sh",
        )
        with open(makefile_in, "w", encoding="utf-8") as f:
            f.write(mi)

        # HMDFS 不支持软链接（ln -sf 被拒）。写一个 ln wrapper 用 cp 模拟其语义：
        # ln 的 src 是相对 linkname(dst) 目录的路径，而 cp 的 src 相对 cwd，
        # 故拼 dirname(dst)/src 得到真实源文件。
        ln_wrapper = os.path.join(self.build_folder, ".ln-wrapper")
        with open(ln_wrapper, "w", encoding="utf-8") as f:
            f.write(
                "#!/bin/sh\n"
                "case \"$1\" in -*) shift ;; esac\n"
                "src=\"$1\"; dst=\"$2\"\n"
                "d=\"${dst%/*}\"\n"
                "[ \"$d\" = \"$dst\" ] && d=\".\"\n"
                "cp -f \"$d/$src\" \"$dst\"\n"
            )
        ln_cmd = f"sh {ln_wrapper}"

        # 供 package() 复用同一套工具链环境（避免 install 阶段用默认 gcc 重编译）。
        self._tc = tc
        self._cc_full = cc_full
        self._tmpdir = tmpdir
        self._ln_cmd = ln_cmd

        # uClibc NPTL 的 gen-as-const 机制依赖 gcc 对 asm 模板的惰性原样输出
        # （@@@name@@@...@@@end@@@ 裸标记），clang 前端会解析 asm 模板而报错。
        # 改用 .ascii + %c0：gcc/clang 都接受 .ascii 指令，%c0 输出整数字符串，sed 仍可提取。
        gen_awk = os.path.join(self.build_folder, "extra", "scripts", "gen-as-const.awk")
        with open(gen_awk, "r", encoding="utf-8") as f:
            ga = f.read()
        ga = ga.replace(
            r'__asm__ (\"@@@name@@@%s',
            r'__asm__ (\".ascii \\\"@@@name@@@%s',
        )
        ga = ga.replace(
            r'@@@value@@@%%0@@@end@@@\"',
            r'@@@value@@@%%c0@@@end@@@\\\\n\\\"\"',
        )
        with open(gen_awk, "w", encoding="utf-8") as f:
            f.write(ga)

        # uClibc CFLAGS 硬编码 -nostdinc（禁用 clang 默认 include），且靠 -I$(KERNEL_HEADERS)
        # 提供内核头文件。改用 clang --target/--sysroot 默认 multilib 路径解析内核头文件
        # （asm/ -> aarch64-linux-ohos/asm/，linux/ 与 asm-generic/ 从 sysroot/usr/include）：
        # 去掉 -nostdinc，并移除空 -I$(KERNEL_HEADERS)。
        rules_mak = os.path.join(self.build_folder, "Rules.mak")
        with open(rules_mak, "r", encoding="utf-8") as f:
            rm = f.read()
        rm = rm.replace(
            "\t-nostdinc -I$(top_builddir)include",
            "\t-I$(top_builddir)include",
        )
        rm = rm.replace(
            "CFLAGS += -I$(KERNEL_HEADERS)",
            "# KERNEL_HEADERS unused: clang --sysroot default path provides kernel headers",
        )
        # uClibc 默认给共享库链接加 -Wl,-z,defs（=--no-undefined），会把 libc.so 对
        # ld-uClibc.so 运行时符号（_dl_pagesize/_dl_phdr/__libc_setup_tls/_dl_aux_init 等）
        # 的 undefined 引用当作错误。GNU ld 容忍、lld 严格；--allow-shlib-undefined 在
        # 部分 lld 版本/顺序下无法覆盖 -z defs。直接去掉 -z defs，让 undefined 由运行时
        # 解析（uclibc 共享库本来就依赖 ld.so 提供的这些符号）。
        rm = rm.replace(
            "LDFLAGS:=$(LDFLAGS_NOSTRIP) -Wl,-z,defs",
            "LDFLAGS:=$(LDFLAGS_NOSTRIP)",
        )
        with open(rules_mak, "w", encoding="utf-8") as f:
            f.write(rm)

        # ldso 的向后兼容链接直接调用 ln -sf（不走 $(LN)/do_ln），HMDFS 上被拒。
        # 两处均为 cd lib 后的同目录软链接，cp -f 替换安全。
        ldso_mk = os.path.join(self.build_folder, "ldso", "ldso", "Makefile.in")
        with open(ldso_mk, "r", encoding="utf-8") as f:
            lm = f.read()
        lm = lm.replace("ln -sf $(UCLIBC_LDSO_NAME)", "cp -f $(UCLIBC_LDSO_NAME)")
        with open(ldso_mk, "w", encoding="utf-8") as f:
            f.write(lm)

        # getopt-susv3.c 使用 gettext 简写宏 _()，但 uClibc 的 libintl.h 未定义 _，
        # gcc 靠隐式声明宽容、clang 把 int->pointer 报 error；补 identity 宏。
        getopt_c = os.path.join(self.build_folder, "libc", "unistd", "getopt-susv3.c")
        with open(getopt_c, "r", encoding="utf-8") as f:
            gc = f.read()
        gc = gc.replace("#include <getopt.h>", "#include <getopt.h>\n#define _(x) (x)")
        with open(getopt_c, "w", encoding="utf-8") as f:
            f.write(gc)

        # allocatestack.c 用 GCC 嵌套函数 check_list（clang 不支持），
        # 提取为文件作用域静态函数，把外层局部变量 elem 作为参数传入。
        import re
        alloc_c = os.path.join(self.build_folder, "libpthread", "nptl", "allocatestack.c")
        with open(alloc_c, "r", encoding="utf-8") as f:
            ac = f.read()
        ac = re.sub(
            r'int check_list \(list_t \*l\).*?\n\s*if \(check_list \(&stack_used\) == 0\)\n\s*\(void\) check_list \(&stack_cache\);',
            'if (check_list (&stack_used, elem) == 0)\n\t    (void) check_list (&stack_cache, elem);',
            ac,
            count=1,
            flags=re.DOTALL,
        )
        ac = ac.replace(
            'void\n__reclaim_stacks (void)\n{',
            'static int\n'
            'check_list (list_t *l, list_t *elem)\n'
            '{\n'
            '  if (l->next->prev != l)\n'
            '    {\n'
            '      assert (l->next->prev == elem);\n'
            '\n'
            '      elem->next = l->next;\n'
            '      elem->prev = l;\n'
            '      l->next = elem;\n'
            '\n'
            '      return 1;\n'
            '    }\n'
            '\n'
            '  return 0;\n'
            '}\n'
            '\n'
            'void\n'
            '__reclaim_stacks (void)\n'
            '{',
        )
        with open(alloc_c, "w", encoding="utf-8") as f:
            f.write(ac)

        # librt/dso_handle.c 定义强符号 __dso_handle，与 clang crtbegin.o 冲突；改为弱符号。
        dso_c = os.path.join(self.build_folder, "librt", "dso_handle.c")
        with open(dso_c, "r", encoding="utf-8") as f:
            dc = f.read()
        dc = dc.replace(
            "const void *const __dso_handle attribute_hidden = &__dso_handle;",
            "const void *const __dso_handle attribute_hidden __attribute__((weak)) = &__dso_handle;",
        )
        with open(dso_c, "w", encoding="utf-8") as f:
            f.write(dc)

        # REALTIME=y + ADVANCED_REALTIME=n 时，uClibc 同时编译 common/clock_gettime.c（简化）
        # 与 librt/clock_gettime.c（完整，经 libc-so-$(REALTIME) 合并），同名 clock_gettime.os 重复。
        # uClibc 意图是 ADVANCED=n 时用 common 版、librt 的 clock_gettime 应被过滤，但 librt 漏了它。
        # 修复：在 librt 的 ADVANCED 过滤列表（与 spawn.c 同组）补上 clock_gettime.c。
        librt_mk = os.path.join(self.build_folder, "librt", "Makefile.in")
        with open(librt_mk, "r", encoding="utf-8") as f:
            lm = f.read()
        lm = lm.replace(
            "$(if $(UCLIBC_HAS_ADVANCED_REALTIME),, \\\n\tspawn.c \\",
            "$(if $(UCLIBC_HAS_ADVANCED_REALTIME),, \\\n\tclock_gettime.c \\\n\tspawn.c \\",
        )
        with open(librt_mk, "w", encoding="utf-8") as f:
            f.write(lm)

        # h_errno 用 __thread + alias（__libc_h_errno），clang emutls 不生成 TLS alias 的
        # __emutls_v. 符号；仿 errno 去掉 alias，netdb.h 的 libc 内部宏改为 identity。
        h_errno_c = os.path.join(self.build_folder, "libc", "misc", "internals", "h_errno.c")
        with open(h_errno_c, "r", encoding="utf-8") as f:
            he = f.read()
        he = he.replace(
            '__thread int h_errno;\nextern __thread int __libc_h_errno __attribute__ ((alias ("h_errno"))) attribute_hidden;',
            '__thread int h_errno attribute_tls_model_ie;',
        )
        with open(h_errno_c, "w", encoding="utf-8") as f:
            f.write(he)

        netdb_h = os.path.join(self.build_folder, "include", "netdb.h")
        with open(netdb_h, "r", encoding="utf-8") as f:
            nh = f.read()
        nh = nh.replace(
            "#    define h_errno __libc_h_errno",
            "#    define h_errno h_errno",
        )
        with open(netdb_h, "w", encoding="utf-8") as f:
            f.write(nh)

        # libc.so 引用了 ldso 的 hidden TLS 符号（_dl_allocate_static_tls 等），
        # 这些由 ld-uClibc.so 在运行时提供；GNU ld 的 -z defs 容忍，lld 报错。
        # 给 libc.so 链接加 --allow-shlib-undefined。
        libc_mk = os.path.join(self.build_folder, "libc", "Makefile.in")
        with open(libc_mk, "r", encoding="utf-8") as f:
            lc = f.read()
        lc = lc.replace(
            "LDFLAGS-libc.so := $(LDFLAGS) $(VERSION_SCRIPT)",
            "LDFLAGS-libc.so := $(LDFLAGS) $(VERSION_SCRIPT) -Wl,--allow-shlib-undefined",
        )
        with open(libc_mk, "w", encoding="utf-8") as f:
            f.write(lc)

        # lld 对 hidden undefined 符号仍报错（--allow-shlib-undefined 无效），
        # 需把 ldso 的 TLS 实现 dl-tls.c 也 include 进 libdl.c（与 ldso.c 同法），
        # 使 _dl_allocate_static_tls/_dl_next_tls_modid 在 libc.so 内定义。
        libdl_c = os.path.join(self.build_folder, "ldso", "libdl", "libdl.c")
        with open(libdl_c, "r", encoding="utf-8") as f:
            ldc = f.read()
        ldc = ldc.replace(
            '#include "../ldso/dl-elf.c"',
            '#include "../ldso/dl-elf.c"\n#include "../ldso/dl-tls.c"',
        )
        with open(libdl_c, "w", encoding="utf-8") as f:
            f.write(ldc)

        # _dl_tlsdesc_return 在 aarch64/dl-tlsdesc.S（汇编），仅进 ldso；libdl.oS 引用它，
        # 需把 dl-tlsdesc.oS 也归档进 libc_so.a（libdl-so-y）。
        libdl_mk = os.path.join(self.build_folder, "ldso", "libdl", "Makefile.in")
        with open(libdl_mk, "r", encoding="utf-8") as f:
            ldm = f.read()
        ldm = ldm.replace(
            "libdl-so-y := $(libdl_OUT)/libdl.oS",
            "libdl-so-y := $(libdl_OUT)/libdl.oS $(top_builddir)ldso/ldso/$(TARGET_ARCH)/dl-tlsdesc.oS",
        )
        with open(libdl_mk, "w", encoding="utf-8") as f:
            f.write(ldm)

        # ldso.c 调用 init_tls() 但无前向声明（声明在 dl-tls.c 的 #ifdef SHARED 里，非头文件），
        # 严格 clang 把隐式声明的 int 返回值赋给 void* 报 -Wint-conversion error。补前向声明。
        ldso_c = os.path.join(self.build_folder, "ldso", "ldso", "ldso.c")
        with open(ldso_c, "r", encoding="utf-8") as f:
            ldc = f.read()
        ldc = ldc.replace(
            '\t\t_dl_debug_early("Calling init_tls()!\\n");\n\t\ttcbp = init_tls ();',
            '\t\textern void *init_tls (void);\n'
            '\t\t_dl_debug_early("Calling init_tls()!\\n");\n\t\ttcbp = init_tls ();',
        )
        with open(ldso_c, "w", encoding="utf-8") as f:
            f.write(ldc)

        # 鸿蒙 PC 内核在静态可执行入口未清零 x0（x0 携带栈/句柄地址，实测非 0）。
        # aarch64 crt1.S 把 x0 当作 rtld_fini 传给 __uClibc_main，退出时 __uClibc_fini
        # 会对该垃圾地址 br 触发 SIGSEGV（所有静态链接程序 exit 时 rc=139）。
        # 静态链接无动态加载器，rtld_fini 应为 NULL；仅共享(Scrt1)路径由 ld.so 经 x0 传入。
        crt1_s = os.path.join(self.build_folder, "libc", "sysdeps", "linux", "aarch64", "crt1.S")
        with open(crt1_s, "r", encoding="utf-8") as f:
            c1 = f.read()
        c1 = c1.replace(
            "\t/* Setup _fini in argument register */\n\tmov\tx5, x0",
            "\t/* rtld_fini: static binaries have no dynamic loader, pass NULL.\n"
            "\t * Only the shared (Scrt1) path carries the loader's atexit fn in x0. */\n"
            "#ifdef L_Scrt1\n"
            "\tmov\tx5, x0\n"
            "#else\n"
            "\tmov\tx5, #0\n"
            "#endif",
        )
        with open(crt1_s, "w", encoding="utf-8") as f:
            f.write(c1)

        # 官方 CI 部分 worker 的文件系统对 .os/.oS 大小写不敏感，二者会互相覆盖导致
        # SHARED 宏分配混乱（.os 误走 SHARED 分支、.oS 误走静态分支）。把 .oS（大写 S）
        # 后缀全局改名为 .oshared（与 .os 不再大小写相似），并保留其 -DSHARED：
        #   - .os（libc.a，静态链接用）无 SHARED，走静态分支；
        #   - .oshared（libc_so.a，共享库用）有 SHARED，走共享分支。
        # 二者文件名不再相似，大小写不敏感下也不会互相覆盖。
        for _root, _dirs, _files in os.walk(self.build_folder):
            for _fn in _files:
                if _fn.startswith("Makefile") or _fn in ("Makerules", "Rules.mak"):
                    _p = os.path.join(_root, _fn)
                    with open(_p, "r", encoding="utf-8") as _f:
                        _c = _f.read()
                    if ".oS" in _c:
                        _c = _c.replace(".oS", ".oshared")
                        with open(_p, "w", encoding="utf-8") as _f:
                            _f.write(_c)

        # 1) 生成 .config（allnoconfig 基线 + 片段）。
        #    conf 是宿主工具，必须用 HOSTCC 编译（设备无 gcc，用 clang）。
        self.run(
            f'make -j1 KCONFIG_ALLCONFIG="{config_file}" ARCH=aarch64 '
            f'HOSTCC="{tc["cc"]}" TMPDIR="{tmpdir}" LN="{ln_cmd}" allnoconfig'
        )

        # 2) 编译。覆盖工具链变量（uClibc Rules.mak 默认 $(CROSS_COMPILE)gcc，
        #    命令行变量优先于 Makefile 的 '=' 赋值）。
        #    注：CI 的 clang 已是 aarch64-linux-ohos 交叉编译器（自带 --target/--sysroot）；
        #    若该 wrapper 未注入三元组，需在 UCLIBC_EXTRA_CFLAGS 补
        #    "--target=aarch64-linux-ohos --sysroot=<sysroot>"。
        self.run(
            f'make -j1 ARCH=aarch64 '
            f'CC="{cc_full}" AR="{tc["ar"]}" NM="{tc["nm"]}" '
            f'OBJDUMP="{tc["objdump"]}" STRIPTOOL="{tc["strip"]}" LD="{tc["ld"]}" '
            f'HOSTCC="{tc["cc"]}" '
            f'UCLIBC_EXTRA_CFLAGS="-O2" TMPDIR="{tmpdir}" LN="{ln_cmd}" '
            f'all'
        )

    def package(self):
        # install = install_runtime + install_dev（含 install_headers + install_startfiles）。
        # PREFIX=$(DESTDIR)（Rules.mak:165），故 DESTDIR 指向 package_folder 完成暂存：
        #   共享库 -> <pkg>/lib，静态库/启动文件 -> <pkg>/usr/lib，头文件 -> <pkg>/usr/include。
        # install 依赖 all，可能触发剩余 .oS 重编译，必须复用 build() 的工具链变量。
        tc = self._tc
        cc_full = self._cc_full
        tmpdir = self._tmpdir
        ln_cmd = self._ln_cmd
        self.run(
            f'make -j1 ARCH=aarch64 '
            f'CC="{cc_full}" AR="{tc["ar"]}" NM="{tc["nm"]}" '
            f'OBJDUMP="{tc["objdump"]}" STRIPTOOL="{tc["strip"]}" LD="{tc["ld"]}" '
            f'HOSTCC="{tc["cc"]}" '
            f'UCLIBC_EXTRA_CFLAGS="-O2" TMPDIR="{tmpdir}" LN="{ln_cmd}" '
            f'DESTDIR="{self.package_folder}" RUNTIME_PREFIX=/ DEVEL_PREFIX=/usr/ '
            f'install'
        )

    def package_info(self):
        self.cpp_info.includedirs = ["usr/include"]
        self.cpp_info.libdirs = ["usr/lib", "lib"]
        self.cpp_info.libs = ["c", "m", "crypt", "pthread", "util", "resolv", "dl", "nsl"]
        # 作为 libc：消费者通常需 -nostdinc/-nostdlib 显式指向本包，避免与系统 musl 混链。
