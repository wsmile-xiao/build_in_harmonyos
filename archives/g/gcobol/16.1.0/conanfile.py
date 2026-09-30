#!/usr/bin/env python3
"""Conan recipe — gcobol 16.1.0（GCC 16 COBOL 语言前端，GCOBOL 编译器）

GCOBOL 前端是 GCC 16 的 COBOL 编译器，源码在 `gcc/cobol/` 目录，不能独立于
GCC 的 gcc 目录构建（cobol1 链接 GCC 后端 `$(BACKEND)`，gcobol 驱动链接
`$(GCC_OBJS)`）。因此本配方做**完整 GCC 16 构建**（`--enable-languages=c,cobol`
`--disable-bootstrap`），用 OHOS 的 clang 作为构建编译器（OHOS 无 gcc）。

与 gcc-ada 9.5.0 的差异：cobol 前端由 C++ 编写，无需 Ada 那类 Alpine GNAT
seed 自举 / XPM loader / 签名代理，clang++ 直接编译 gcc/cobol 源码。

关键适配点（OHOS 特有，同 libgcobol/gcc-ada 经验）：
  - HMDFS 无执行位（E046/E087）→ configure 用 /bin/sh 执行；
  - config.status 临时目录（E011/E052/E060）→ patch mktemp 到 $TMPDIR；
  - LLVM-only 工具链（E012）→ export AR=llvm-ar 等；
  - clang 构建 GCC 源码 → --disable-werror 规避 GCC 特有告警；
  - cobol1 链接 libcommon.a，stderr copy relocation 对齐失败 → -fPIC 编译；
  - OHOS 是 musl：驱动默认动态链接器是 glibc 的 /lib/ld-linux-aarch64.so.1，
    gcobol 驱动 wrapper 加 -mmusl 切到 /lib/ld-musl-aarch64.so.1；
  - libgcobol 是 C++ 库，gcobol 构建无 cc1plus → 用 clang++ 手动构建；
  - OHOS 动态链接器不认未签名的 .so → package() 对全部 ELF 签名。
"""
import os
import re
import shlex
import shutil
import stat
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import build_jobs
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


class GcobolConan(ConanFile):
    name = "gcobol"
    version = "16.1.0"
    package_type = "application"
    description = "GNU Compiler Collection 16 COBOL compiler (GCOBOL)"
    license = "GPL-3.0-or-later WITH GCC-exception-3.1"
    homepage = "https://gcc.gnu.org/"
    url = "https://gcc.gnu.org/"

    settings = "os", "compiler", "build_type", "arch"

    _target_triplet = "aarch64-linux-ohos"
    _ohos_sysroot = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot"
    _ohos_llvm = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm"
    _tmpdir = "/data/storage/el2/base/cache"

    def validate(self):
        if str(self.settings.os) != "OHOS":
            raise ConanInvalidConfiguration(
                "gcobol is prepared for a native OHOS build only")

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # libgcobol 运行时依赖 libxml2；链接/运行期都需要其 include/lib。
        self.requires("libxml2/2.15.3")

    def source(self):
        src = self.conan_data["sources"]["16.1.0"]
        get(self, url=src["gcc"]["url"], sha256=src["gcc"]["sha256"], strip_root=True)
        for name in ("gmp", "mpfr", "mpc"):
            get(
                self,
                url=src[name]["url"],
                sha256=src[name]["sha256"],
                strip_root=True,
                destination=os.path.join(self.source_folder, name),
            )
        # patch 必须在 source() 里完成（而非 build()）：不同 conan 版本对
        # build() 阶段 self.source_folder 是否仍是下载原始源码语义不同，有的
        # 会先复制 source→build 再编译，导致 build() 里的 patch 落在原始目录、
        # 而编译用的是复制后的未 patch 目录（CI 上 __availability__ 屏蔽失效
        # 的根因）。在 source() 末尾 patch 原始源码，复制到 build 目录时自然
        # 带上 patch。
        self._patch_ohos_sources()

    def _configure_args(self):
        return [
            "--prefix=/",
            "--libdir=/lib",
            "--libexecdir=/libexec",
            "--build={}".format(self._target_triplet),
            "--host={}".format(self._target_triplet),
            "--target={}".format(self._target_triplet),
            "--enable-languages=c,cobol",
            "--enable-threads=posix",
            # host 代码编译为 PIC（gcc/configure 里 enable_host_shared=yes →
            # PICFLAG=-fPIC）。OHOS 上 stderr 等 libc 符号 copy relocation 到
            # .bss 时要求 8 字节对齐，非 PIC 的 LDST64 绝对寻址会触发 lld
            # "improper alignment for R_AARCH64_LDST64_ABS_LO12_NC" 链接失败；
            # 用官方 --enable-host-shared 让 PICFLAG=-fPIC 走 GOT 规避。
            "--enable-host-shared",
            "--disable-bootstrap",
            "--disable-lto",
            "--disable-plugin",
            "--disable-multilib",
            "--disable-nls",
            # CI worker 无 texi2pod/makeinfo，gcc.pod 等文档生成会失败
            # （all-gcc 在 rm gcc.pod 后 Error 2）；本包只发布编译器二进制，
            # 不需要 .pod/info/man 文档，禁用文档生成。
            "--disable-doc",
            "--disable-shared",
            "--disable-libatomic",
            "--disable-libitm",
            "--disable-libsanitizer",
            "--disable-libgomp",
            "--disable-libquadmath",
            "--disable-libssp",
            "--disable-libvtv",
            "--disable-werror",
            "--without-isl",
            "--with-sysroot={}".format(self._ohos_sysroot),
            "--with-native-system-header-dir=/usr/include",
        ]

    def _patch_ohos_sources(self):
        """GCC 16 OHOS 源码适配（真机手动构建已验证的完整 patch 集）。"""
        import glob
        src = self.source_folder

        # 0. cobol 前端 .cc：屏蔽 OHOS 系统头的 clang 扩展属性 __availability__。
        #    cobol1 前端的 14 个 .cc（cobol1/genapi/genutil/gengen/genmath/…）每个
        #    都以 #include "cobol-system.h" 开头，经其 → stdio.h 引入
        #    __attribute__((__availability__(ohos,introduced=…)))。cobol1 编译
        #    COBOL 程序时把该属性输出到 .s 的 .size 指令 → 汇编器报
        #    "unrecognized symbol type" / "unknown mnemonic __availability__"。
        #    在每个 .cc 的第一个 #include 之前把 __availability__(...) 定义为空
        #    （cobol-system.h 是所有源文件最先 include 系统头的地方，必须在这里
        #    屏蔽，libgcobol 头文件太晚）。
        for _cc in glob.glob(os.path.join(src, "gcc", "cobol", "*.cc")):
            with open(_cc, "r", errors="surrogateescape") as _f:
                _t = _f.read()
            if "__availability__" in _t:
                continue
            _idx = _t.find("#include")
            if _idx < 0:
                continue
            _inject = (
                "/* OHOS: mask Clang's __availability__ attribute "
                "(GCC cobol1 cannot parse it). */\n"
                "#define __availability__(...)\n\n"
            )
            _t = _t[:_idx] + _inject + _t[_idx:]
            with open(_cc, "w", errors="surrogateescape") as _f:
                _f.write(_t)

        # 0b. gcobolspec.cc：链接 COBOL 程序时 STDCPP_LIBRARY 默认 "stdc++"，
        #     OHOS 是 musl + libc++，-lstdc++ 找不到；libgcobol.so 已链接
        #     libc++，这里改成 "c++"（链接只 -lc++）。
        gspec = os.path.join(src, "gcc", "cobol", "gcobolspec.cc")
        if os.path.isfile(gspec):
            with open(gspec, "r", errors="surrogateescape") as _f:
                _t = _f.read()
            _t = _t.replace('#define STDCPP_LIBRARY "stdc++"',
                            '#define STDCPP_LIBRARY "c++"', 1)
            with open(gspec, "w", errors="surrogateescape") as _f:
                _f.write(_t)

        # 1. config.sub 注入 ohos triplet（E122）
        scripts = []
        for name in ("config.sub", "configfsf.sub"):
            scripts += glob.glob(os.path.join(src, "**", name), recursive=True)
        for script in scripts:
            with open(script, "r", errors="surrogateescape") as f:
                content = f.read()
            marker = "# HarmonyOS triplet compatibility (Conan recipe)"
            if marker in content:
                continue
            snippet = (
                "\n{marker}\n"
                'case "$1" in\n'
                "  aarch64-linux-ohos | aarch64-unknown-linux-ohos | "
                "none-unknown-linux-ohos)\n"
                "    echo aarch64-unknown-linux-ohos\n"
                "    exit 0\n"
                "    ;;\n"
                "esac\n"
            ).format(marker=marker)
            newline = content.find("\n")
            if newline < 0:
                continue
            with open(script, "w", errors="surrogateescape") as f:
                f.write(content[: newline + 1] + snippet + content[newline + 1:])

        # 2. 所有 configure 的 mktemp -> $TMPDIR
        for configure in glob.glob(os.path.join(src, "**", "configure"), recursive=True):
            with open(configure, "r", errors="surrogateescape") as f:
                t = f.read()
            fixed = t.replace(
                'mktemp -d "./confXXXXXX"', 'mktemp -d "$TMPDIR/confXXXXXX"'
            )
            fixed = fixed.replace(
                "tmp=./conf$$-$RANDOM", "tmp=$TMPDIR/conf$$-$RANDOM"
            )
            if fixed != t:
                with open(configure, "w", errors="surrogateescape") as f:
                    f.write(fixed)

        # 3. move-if-change 通过 $(SHELL)
        move_pat = re.compile(
            r"(?<!\$\(SHELL\) )\$\(srcdir\)/\.\./move-if-change")
        for mk in glob.glob(os.path.join(src, "**", "Makefile.in"), recursive=True) + \
                glob.glob(os.path.join(src, "**", "Make-lang.in"), recursive=True):
            with open(mk, "r", errors="surrogateescape") as f:
                t = f.read()
            fixed = move_pat.sub("$(SHELL) $(srcdir)/../move-if-change", t)
            if fixed != t:
                with open(mk, "w", errors="surrogateescape") as f:
                    f.write(fixed)

        # 4. gmp m4-ccas 通过 $(SHELL)
        m4_path = os.path.join(src, "gmp", "mpn", "Makefile.in")
        if os.path.isfile(m4_path):
            with open(m4_path, "r", errors="surrogateescape") as f:
                t = f.read()
            direct = ("\t$(LIBTOOL) --mode=compile --tag=CC "
                      "$(top_srcdir)/mpn/m4-ccas ")
            through = ("\t$(LIBTOOL) --mode=compile --tag=CC "
                       "$(SHELL) $(top_srcdir)/mpn/m4-ccas ")
            if direct in t and through not in t:
                with open(m4_path, "w", errors="surrogateescape") as f:
                    f.write(t.replace(direct, through, 1))

        # 5. mpfr get_patches.sh 通过 $(SHELL)
        mpfr_mk = os.path.join(src, "mpfr", "src", "Makefile.in")
        if os.path.isfile(mpfr_mk):
            with open(mpfr_mk, "r", errors="surrogateescape") as f:
                t = f.read()
            direct = "\t$(GET_PATCHES_SH) $(PATCHES) > $@"
            through = "\t$(SHELL) $(GET_PATCHES_SH) $(PATCHES) > $@"
            if direct in t and through not in t:
                with open(mpfr_mk, "w", errors="surrogateescape") as f:
                    f.write(t.replace(direct, through, 1))

        # 6. lexio.cc 用 libstdc++ ext/stdio_filebuf.h（__gnu_cxx::stdio_filebuf），
        #    OHOS libc++ 无此 GNU 扩展，内联 minimal write-only shim。必须 setvbuf
        #    为 unbuffered：输出临时文件靠 re-map fd 读回，若走 stdio 缓冲且程序
        #    无 COPY（不触发 out.flush()），缓冲内容丢失 → 词法器看到空文件 →
        #    "expecting IDENTIFICATION DIVISION"。
        lexio = os.path.join(src, "gcc", "cobol", "lexio.cc")
        _stdio_stub = (
            "// OHOS libc++ has no ext/stdio_filebuf.h; minimal write-only shim.\n"
            "#include <streambuf>\n#include <ostream>\n#include <cstdio>\n"
            "namespace __gnu_cxx {\n"
            "template<typename _CharT, typename _Traits = std::char_traits<_CharT> >\n"
            "class stdio_filebuf : public std::basic_streambuf<_CharT, _Traits> {\n"
            "  FILE* _file; std::ios_base::openmode _mode;\n"
            "public:\n"
            "  typedef _CharT char_type; typedef _Traits traits_type;\n"
            "  typedef typename traits_type::int_type int_type;\n"
            "  stdio_filebuf(FILE* f, std::ios_base::openmode m) : _file(f), _mode(m) {\n"
            "    if (_file) setvbuf(_file, NULL, _IONBF, 0);\n"
            "  }\n"
            "  ~stdio_filebuf() { if (_file) fflush(_file); }\n"
            "protected:\n"
            "  virtual int_type overflow(int_type c = traits_type::eof()) {\n"
            "    if (!(_mode & std::ios_base::out) || !_file) return traits_type::eof();\n"
            "    if (!traits_type::eq_int_type(c, traits_type::eof())) {\n"
            "      char ch = traits_type::to_char_type(c);\n"
            "      if (fwrite(&ch, 1, 1, _file) != 1) return traits_type::eof();\n"
            "    }\n"
            "    return traits_type::not_eof(c);\n"
            "  }\n"
            "  virtual std::streamsize xsputn(const char_type* s, std::streamsize n) {\n"
            "    if (!(_mode & std::ios_base::out) || !_file) return 0;\n"
            "    return (std::streamsize)fwrite(s, 1, (size_t)n, _file);\n"
            "  }\n"
            "  virtual int sync() { if (_file) { fflush(_file); return 0; } return -1; }\n"
            "};\n}\n"
        )
        if os.path.isfile(lexio):
            with open(lexio, "r", errors="surrogateescape") as f:
                t = f.read()
            if "minimal write-only shim" not in t:
                if "#include <ext/stdio_filebuf.h>" in t:
                    t = t.replace("#include <ext/stdio_filebuf.h>\n", _stdio_stub)
                else:
                    anchor = '#include "config.h"\n'
                    if anchor in t:
                        t = t.replace(anchor, anchor + _stdio_stub, 1)
                with open(lexio, "w", errors="surrogateescape") as f:
                    f.write(t)

        # 7. defaults.h: GCC 16 把 stack-check 默认宏放进 #ifdef GCC_INSN_FLAGS_H
        #    块，未先 include insn-flags.h 的文件会丢失 STACK_CHECK_MAX_VAR_SIZE。
        defaults = os.path.join(src, "gcc", "defaults.h")
        if os.path.isfile(defaults):
            with open(defaults, "r", errors="surrogateescape") as f:
                t = f.read()
            anchor = "#ifdef GCC_INSN_FLAGS_H\n"
            if "OHOS stack-check unconditional" not in t and anchor in t:
                snip = (
                    "/* OHOS stack-check unconditional defaults */\n"
                    "#ifndef STACK_CHECK_MAX_VAR_SIZE\n#define STACK_CHECK_MAX_VAR_SIZE 40\n#endif\n"
                    "#ifndef STACK_CHECK_MAX_FRAME_SIZE\n#define STACK_CHECK_MAX_FRAME_SIZE 4088\n#endif\n"
                    "#ifndef STACK_CHECK_PROBE_INTERVAL_EXP\n#define STACK_CHECK_PROBE_INTERVAL_EXP 12\n#endif\n"
                    "#ifndef STACK_CHECK_STATIC_BUILTIN\n#define STACK_CHECK_STATIC_BUILTIN 0\n#endif\n"
                    "#ifndef STACK_CHECK_BUILTIN\n#define STACK_CHECK_BUILTIN 0\n#endif\n\n"
                )
                t = t.replace(anchor, snip + anchor, 1)
                with open(defaults, "w", errors="surrogateescape") as f:
                    f.write(t)

        # 8. symbols.cc: symbol-table 临时文件用 tmpfile()，HMDFS 上失败；改走
        #    GCOBOL_TEMPDIR + mkstemp（与 lexio.cc 一致）。
        symbols = os.path.join(src, "gcc", "cobol", "symbols.cc")
        if os.path.isfile(symbols):
            with open(symbols, "r", errors="surrogateescape") as f:
                t = f.read()
            old = """    FILE *mapped;
    if( (mapped = tmpfile()) == NULL ) {
      cbl_err( "could not create temporary file for symbol table");
    }
"""
            new = """    FILE *mapped = NULL;
    char *tdir = getenv("GCOBOL_TEMPDIR");
    if( tdir && 0 != strcmp(tdir, "/") ) {
      char *stem = xasprintf("%sXXXXXX", tdir);
      int fd = mkstemp(stem);
      if( -1 == fd ) {
        cbl_err( "could not create temporary file for symbol table '%s'", tdir );
      }
      mapped = fdopen(fd, "w+");
    } else {
      mapped = tmpfile();
    }
    if( mapped == NULL ) {
      cbl_err( "could not create temporary file for symbol table");
    }
"""
            if old in t:
                t = t.replace(old, new, 1)
                with open(symbols, "w", errors="surrogateescape") as f:
                    f.write(t)

        # 9. libgcc lse-init.c: 用 __getauxval（glibc 内部符号），OHOS musl 动态
        #    libc.so 只导出 getauxval → 链接失败。改用公开的 getauxval。
        lse = os.path.join(src, "libgcc", "config", "aarch64", "lse-init.c")
        if os.path.isfile(lse):
            with open(lse, "r", errors="surrogateescape") as f:
                t = f.read()
            old = "unsigned long int __getauxval (unsigned long int);\n"
            new = ("/* OHOS musl exports getauxval, not glibc's internal __getauxval. */\n"
                   "unsigned long int getauxval (unsigned long int);\n")
            if old in t:
                t = t.replace(old, new, 1)
                t = t.replace(
                    "unsigned long hwcap = __getauxval (AT_HWCAP);",
                    "unsigned long hwcap = getauxval (AT_HWCAP);",
                    1,
                )
                with open(lse, "w", errors="surrogateescape") as f:
                    f.write(t)

        # 10. libgcc gthr-posix.h: OHOS 不支持 pthread_cancel，且需 GTHR_ACTIVE_PROXY。
        gthr = os.path.join(src, "libgcc", "gthr-posix.h")
        if os.path.isfile(gthr):
            with open(gthr, "r", errors="surrogateescape") as f:
                t = f.read()
            repls = (
                (
                    "#ifndef __BIONIC__\n__gthrw(pthread_cancel)\n#endif",
                    "#if !defined (__BIONIC__) && !defined (__OHOS__)\n__gthrw(pthread_cancel)\n#endif",
                ),
                (
                    "#elif defined (__BIONIC__)\n# define GTHR_ACTIVE_PROXY\t__gthrw_(pthread_create)",
                    "#elif defined (__BIONIC__) || defined (__OHOS__)\n# define GTHR_ACTIVE_PROXY\t__gthrw_(pthread_create)",
                ),
            )
            changed = False
            for old, new in repls:
                if new not in t and old in t:
                    t = t.replace(old, new, 1)
                    changed = True
            if changed:
                with open(gthr, "w", errors="surrogateescape") as f:
                    f.write(t)

        # 11. libgcc mkheader.sh 通过 $(SHELL)
        lg_mk = os.path.join(src, "libgcc", "Makefile.in")
        if os.path.isfile(lg_mk):
            with open(lg_mk, "r", errors="surrogateescape") as f:
                t = f.read()
            direct = "\t\t$(srcdir)/mkheader.sh > tmp-libgcc_tm.h"
            through = "\t\t$(SHELL) $(srcdir)/mkheader.sh > tmp-libgcc_tm.h"
            if direct in t and through not in t:
                t = t.replace(direct, through, 1)
            # unwind_h: 去掉 'sh $(SHELL)' 双重 shell
            bad = "\tsh $(SHELL) $(srcdir)/../move-if-change $$dest $(gcc_objdir)/include/unwind.h"
            good = "\t$(SHELL) $(srcdir)/../move-if-change $$dest $(gcc_objdir)/include/unwind.h"
            if bad in t:
                t = t.replace(bad, good, 1)
            with open(lg_mk, "w", errors="surrogateescape") as f:
                f.write(t)

        # 12. libgcobol.cc: _Float32/_Float64（C23 类型）→ float/double（libc++ 不支持）
        lgc = os.path.join(src, "libgcobol", "libgcobol.cc")
        if os.path.isfile(lgc):
            with open(lgc, "r", errors="surrogateescape") as f:
                t = f.read()
            fixed = t.replace("_Float32", "float").replace("_Float64", "double")
            if fixed != t:
                with open(lgc, "w", errors="surrogateescape") as f:
                    f.write(fixed)

        # 13. genapi.cc psa_global() 用 _tolower()（glibc 无条件 c+0x20 宏），把
        #     '_'(0x5F) 误转成 0x7F(DEL)，生成的 __ggsr__<name> 符号名含 DEL →
        #     aarch64 GNU as 2.45 拒绝（"bad expression"）。改用 GCC 的 TOLOWER
        #     （safe-ctype.h 查表，非字母原样返回）。
        genapi = os.path.join(src, "gcc", "cobol", "genapi.cc")
        if os.path.isfile(genapi):
            with open(genapi, "r", errors="surrogateescape") as f:
                t = f.read()
            fixed = t.replace("ach[i] = _tolower(ach[i]);",
                              "ach[i] = TOLOWER(ach[i]);")
            if fixed != t:
                with open(genapi, "w", errors="surrogateescape") as f:
                    f.write(fixed)

        # 14. OHOS musl 的 iconv 不支持 CP1140（EBCDIC），但 gcobol 内置了
        #     CP1252<->CP1140 映射表。charmap_t / __gg__iconverter / reencode /
        #     encode 在 iconv_open 失败（返回 (iconv_t)-1）后仍调用 iconv →
        #     段错误或 "cannot convert" 报错。加失败检查，CP1140 回退内置表。
        # 14a. charmaps.h: charmap_t 构造函数两处 iconv_open 检查。
        charmaps_h = os.path.join(src, "libgcobol", "charmaps.h")
        if os.path.isfile(charmaps_h):
            with open(charmaps_h, "r", errors="surrogateescape") as f:
                t = f.read()
            if "This platform's iconv lacks CP1140" not in t:
                old = (
                    "      /*size_t nret = */ iconv( cd,\n"
                    "                            &inbuf,  &inbytesleft,\n"
                    "                            &outbuf, &outbytesleft);\n"
                    "      outlength = sizeof(response_) - outbytesleft;\n"
                    "      iconv_close(cd);\n"
                )
                new = (
                    "      if( cd != (iconv_t)-1 )\n"
                    "        {\n"
                    "        /*size_t nret = */ iconv( cd,\n"
                    "                              &inbuf,  &inbytesleft,\n"
                    "                              &outbuf, &outbytesleft);\n"
                    "        outlength = sizeof(response_) - outbytesleft;\n"
                    "        iconv_close(cd);\n"
                    "        }\n"
                    "      else if( m_encoding == iconv_CP1140_e )\n"
                    "        {\n"
                    "        // This platform's iconv lacks CP1140 (e.g. musl\n"
                    "        // libc).  Use the built-in tables instead; CP1140\n"
                    "        // is single-byte EBCDIC whose digit zero is 0xF0.\n"
                    "        outlength = 1;\n"
                    "        response_[0] = static_cast<char>(0xF0);\n"
                    "        }\n"
                )
                t = t.replace(old, new, 1)
                old2 = (
                    "      iconv(cd,\n"
                    "            &inbuf,  &inbytesleft,\n"
                    "            &outbuf, &outbytesleft);\n"
                    "      outlength = sizeof(response_) - outbytesleft;\n"
                    "      iconv_close(cd);\n"
                    "      m_is_like_utf8 = (outlength == 3);\n"
                )
                new2 = (
                    "      if( cd != (iconv_t)-1 )\n"
                    "        {\n"
                    "        iconv(cd,\n"
                    "              &inbuf,  &inbytesleft,\n"
                    "              &outbuf, &outbytesleft);\n"
                    "        outlength = sizeof(response_) - outbytesleft;\n"
                    "        iconv_close(cd);\n"
                    "        }\n"
                    "      else\n"
                    "        {\n"
                    "        outlength = 0;\n"
                    "        }\n"
                    "      m_is_like_utf8 = (outlength == 3);\n"
                )
                t = t.replace(old2, new2, 1)
                with open(charmaps_h, "w", errors="surrogateescape") as f:
                    f.write(t)

        # 14b. charmaps.cc: __gg__iconverter iconv_open 失败回退内置表。
        charmaps_cc = os.path.join(src, "libgcobol", "charmaps.cc")
        if os.path.isfile(charmaps_cc):
            with open(charmaps_cc, "r", errors="surrogateescape") as f:
                t = f.read()
            if "goto iconvert_done" not in t:
                old = (
                    "    else\n"
                    "      {\n"
                    "      // We've seen this pairing before.\n"
                    "      cd = it->second;\n"
                    "      }\n"
                    "\n"
                    "    char *inbuf  = const_cast<char *>(str);\n"
                )
                new = (
                    "    else\n"
                    "      {\n"
                    "      // We've seen this pairing before.\n"
                    "      cd = it->second;\n"
                    "      }\n"
                    "\n"
                    "    if( cd == (iconv_t)-1 )\n"
                    "      {\n"
                    "      // This platform's iconv lacks the requested encoding\n"
                    "      // (e.g. CP1140 on musl libc).  Use the built-in\n"
                    "      // single-byte tables for CP1252<->CP1140.\n"
                    "      const unsigned short *tbl = nullptr;\n"
                    "      if( from == iconv_CP1252_e && to == iconv_CP1140_e )\n"
                    "        {\n"
                    "        tbl = __gg__cp1252_to_cp1140_values;\n"
                    "        }\n"
                    "      else if( from == iconv_CP1140_e && to == iconv_CP1252_e )\n"
                    "        {\n"
                    "        tbl = __gg__cp1140_to_cp1252_values;\n"
                    "        }\n"
                    "      if( tbl )\n"
                    "        {\n"
                    "        for( size_t i = 0; i < length; i++ )\n"
                    "          {\n"
                    "          retval[i] = static_cast<char>(tbl[static_cast<unsigned char>(str[i])] & 0xFF);\n"
                    "          }\n"
                    "        outlength = length;\n"
                    "        iconv_retval = 0;\n"
                    "        }\n"
                    "      else if( from == iconv_CP1140_e )\n"
                    "        {\n"
                    "        // Two-step: CP1140 -> CP1252 (built-in) -> <to> (iconv).\n"
                    "        char *tmp = static_cast<char *>(malloc(length));\n"
                    "        for( size_t i = 0; i < length; i++ )\n"
                    "          {\n"
                    "          tmp[i] = static_cast<char>(__gg__cp1140_to_cp1252_values[\n"
                    "              static_cast<unsigned char>(str[i])] & 0xFF);\n"
                    "          }\n"
                    "        iconv_t cd2 = iconv_open(__gg__encoding_iconv_name(to), \"CP1252\");\n"
                    "        if( cd2 != (iconv_t)-1 )\n"
                    "          {\n"
                    "          char *in2 = tmp;\n"
                    "          char *out2 = retval;\n"
                    "          size_t inl2 = length;\n"
                    "          size_t outl2 = retsize;\n"
                    "          iconv(cd2, &in2, &inl2, &out2, &outl2);\n"
                    "          outlength = retsize - outl2;\n"
                    "          iconv_close(cd2);\n"
                    "          }\n"
                    "        else\n"
                    "          {\n"
                    "          outlength = 0;\n"
                    "          }\n"
                    "        iconv_retval = 0;\n"
                    "        free(tmp);\n"
                    "        }\n"
                    "      else if( to == iconv_CP1140_e )\n"
                    "        {\n"
                    "        // Two-step: <from> -> CP1252 (iconv) -> CP1140 (built-in).\n"
                    "        iconv_t cd2 = iconv_open(\"CP1252\", __gg__encoding_iconv_name(from));\n"
                    "        if( cd2 != (iconv_t)-1 )\n"
                    "          {\n"
                    "          char *in2 = const_cast<char *>(str);\n"
                    "          char *out2 = retval;\n"
                    "          size_t inl2 = length;\n"
                    "          size_t outl2 = retsize;\n"
                    "          iconv(cd2, &in2, &inl2, &out2, &outl2);\n"
                    "          size_t n2 = retsize - outl2;\n"
                    "          iconv_close(cd2);\n"
                    "          for( size_t i = 0; i < n2; i++ )\n"
                    "            {\n"
                    "            retval[i] = static_cast<char>(__gg__cp1252_to_cp1140_values[\n"
                    "                static_cast<unsigned char>(retval[i])] & 0xFF);\n"
                    "            }\n"
                    "          outlength = n2;\n"
                    "          }\n"
                    "        else\n"
                    "          {\n"
                    "          outlength = 0;\n"
                    "          }\n"
                    "        iconv_retval = 0;\n"
                    "        }\n"
                    "      else\n"
                    "        {\n"
                    "        outlength = 0;\n"
                    "        iconv_retval = static_cast<size_t>(-1);\n"
                    "        }\n"
                    "      goto iconvert_done;\n"
                    "      }\n"
                    "\n"
                    "    char *inbuf  = const_cast<char *>(str);\n"
                )
                t = t.replace(old, new, 1)
                old2 = (
                    "  retval[outlength+0] = '\\0';\n"
                    "  retval[outlength+1] = '\\0';\n"
                    "  retval[outlength+2] = '\\0';\n"
                    "  retval[outlength+3] = '\\0';\n"
                )
                new2 = (
                    "iconvert_done:\n"
                    "  retval[outlength+0] = '\\0';\n"
                    "  retval[outlength+1] = '\\0';\n"
                    "  retval[outlength+2] = '\\0';\n"
                    "  retval[outlength+3] = '\\0';\n"
                )
                t = t.replace(old2, new2, 1)
                with open(charmaps_cc, "w", errors="surrogateescape") as f:
                    f.write(t)

        # 14c. symbols.cc: reencode（collating sequence）与 encode（VALUE 字面量）
        #      的 CP1140 转换回退内置表。
        symbols_cc = os.path.join(src, "gcc", "cobol", "symbols.cc")
        if os.path.isfile(symbols_cc):
            with open(symbols_cc, "r", errors="surrogateescape") as f:
                t = f.read()
            if "builtin_cp1140" not in t:
                old = (
                    "  iconv_t cd = iconv_open(tocode, fromcode);\n"
                    "\n"
                    "  const charmap_t *charmap_disp =\n"
                )
                new = (
                    "  iconv_t cd = iconv_open(tocode, fromcode);\n"
                    "  const bool builtin_cp1140 =\n"
                    "      (cd == (iconv_t)-1\n"
                    "       && current_encoding(display_encoding_e) == iconv_CP1140_e);\n"
                    "\n"
                    "  const charmap_t *charmap_disp =\n"
                )
                t = t.replace(old, new, 1)
                old2 = (
                    "    size_t n = iconv(cd, &inbuf, &inbytesleft, &outbuf, &outbytesleft);\n"
                    "\n"
                    "    if( n == size_t(-1) ) {\n"
                    "      error_msg(loc, \"%s character '%c' (%x hex) cannot be converted to %s\",\n"
                    "                fromcode, ch, ch, tocode);\n"
                    "      continue;\n"
                    "    }\n"
                    "    if( n != 0 ) {\n"
                    "      dbgmsg(\"%s character '%c' (%x hex) irreversibly converted to %s\",\n"
                    "             fromcode, ch, ch, tocode);\n"
                    "    }\n"
                    "    assert(outbytesleft < sizeof(pos));\n"
                    "    n = sizeof(pos) - outbytesleft;\n"
                    "    if( stride < n ) {\n"
                    "      error_msg(loc, \"%s character '%c' (%x hex) requires %zu bytes as %s\",\n"
                    "                fromcode, ch, ch, n, tocode);\n"
                    "      continue;\n"
                    "    }\n"
                )
                new2 = (
                    "    size_t n;\n"
                    "    if( builtin_cp1140 )\n"
                    "      {\n"
                    "      pos[0] = static_cast<unsigned char>(__gg__cp1252_to_cp1140_values[ch] & 0xFF);\n"
                    "      n = 1;\n"
                    "      }\n"
                    "    else\n"
                    "      {\n"
                    "      n = iconv(cd, &inbuf, &inbytesleft, &outbuf, &outbytesleft);\n"
                    "\n"
                    "      if( n == size_t(-1) ) {\n"
                    "        error_msg(loc, \"%s character '%c' (%x hex) cannot be converted to %s\",\n"
                    "                  fromcode, ch, ch, tocode);\n"
                    "        continue;\n"
                    "      }\n"
                    "      if( n != 0 ) {\n"
                    "        dbgmsg(\"%s character '%c' (%x hex) irreversibly converted to %s\",\n"
                    "               fromcode, ch, ch, tocode);\n"
                    "      }\n"
                    "      assert(outbytesleft < sizeof(pos));\n"
                    "      n = sizeof(pos) - outbytesleft;\n"
                    "      if( stride < n ) {\n"
                    "        error_msg(loc, \"%s character '%c' (%x hex) requires %zu bytes as %s\",\n"
                    "                  fromcode, ch, ch, n, tocode);\n"
                    "        continue;\n"
                    "      }\n"
                    "      }\n"
                )
                t = t.replace(old2, new2, 1)
                old3 = (
                    "    iconv_t cd = iconv_cd(codeset.encoding);\n"
                    "    if( cd == iconv_t(-1) ) {\n"
                    "      error_msg(loc, \"cannot convert from %qs to %qs: %s\",\n"
                    "                cbl_encoding_str(src->type),\n"
                    "                cbl_encoding_str(codeset.encoding),\n"
                    "                xstrerror(errno));\n"
                    "      continue;\n"
                    "    }\n"
                )
                new3 = (
                    "    iconv_t cd = iconv_cd(codeset.encoding);\n"
                    "    if( cd == iconv_t(-1) ) {\n"
                    "      if( codeset.encoding == iconv_CP1140_e )\n"
                    "        {\n"
                    "        // This platform's iconv lacks CP1140 (e.g. musl\n"
                    "        // libc).  Use the built-in CP1252->CP1140 table.\n"
                    "        size_t n = srclen;\n"
                    "        if( n > static_cast<size_t>(data.capacity()) ) n = data.capacity();\n"
                    "        for( size_t i = 0; i < n; i++ )\n"
                    "          {\n"
                    "          const_cast<char*>(data.initial)[i] = static_cast<char>(\n"
                    "              __gg__cp1252_to_cp1140_values[\n"
                    "                  static_cast<unsigned char>(data.original()[i])] & 0xFF);\n"
                    "          }\n"
                    "        return nullptr; // success via built-in table\n"
                    "        }\n"
                    "      error_msg(loc, \"cannot convert from %qs to %qs: %s\",\n"
                    "                cbl_encoding_str(src->type),\n"
                    "                cbl_encoding_str(codeset.encoding),\n"
                    "                xstrerror(errno));\n"
                    "      continue;\n"
                    "    }\n"
                )
                t = t.replace(old3, new3, 1)
                with open(symbols_cc, "w", errors="surrogateescape") as f:
                    f.write(t)

        # 15. libgcobol.cc float128_to_int128：用 musl 的 powl(10,rdigits) 缩放
        #     intermediate 值，powl(10,31) 在 musl 上 ≈ 9.9999e30（精度不足），
        #     导致 MAX/MIN 等 intrinsic 返回 7.9999... 而非 8。改用精确的
        #     __gg__power_of_ten（int128 10 次幂表）。
        lgc_main = os.path.join(src, "libgcobol", "libgcobol.cc")
        if os.path.isfile(lgc_main):
            with open(lgc_main, "r", errors="surrogateescape") as f:
                t = f.read()
            old = ("    value *= FP128_FUNC(pow)(GCOB_FP128_LITERAL (10.0), "
                   "(GCOB_FP128)(*rdigits));\n")
            new = "    value *= (GCOB_FP128)__gg__power_of_ten(*rdigits);\n"
            if old in t:
                t = t.replace(old, new, 1)
                with open(lgc_main, "w", errors="surrogateescape") as f:
                    f.write(t)

        # 16. util.cc cdf_literalize：字符串 CDF 值（>>DEFINE x AS "str"）只设
        #     data.original 没设 data.initial，symbol_field_add 断言
        #     "!is_literal(field) || field->data.initial" 触发 ICE（如 libgcobol
        #     compat/t/smoke.cbl 的 >>DEFINE FILENAME AS "..."）。改用 5 参构造
        #     让 initial == original。
        util_cc = os.path.join(src, "gcc", "cobol", "util.cc")
        if os.path.isfile(util_cc):
            with open(util_cc, "r", errors="surrogateescape") as f:
                t = f.read()
            old = (
                "      auto len = strlen(value.string);\n"
                "      cbl_field_data_t data(len, len);\n"
                "      data.original(xstrdup(value.string));\n"
                "      field = cbl_field_t{ FldLiteralA, constant_e, data, 0, name.c_str() };\n"
            )
            new = (
                "      auto s = xstrdup(value.string);\n"
                "      auto len = strlen(s);\n"
                "      cbl_field_data_t data(len, len, 0, 0, s);\n"
                "      field = cbl_field_t{ FldLiteralA, constant_e, data, 0, name.c_str() };\n"
            )
            if old in t:
                t = t.replace(old, new, 1)
                with open(util_cc, "w", errors="surrogateescape") as f:
                    f.write(t)

        # 17. symfind.cc：用户声明的字段若与预定义全局寄存器（RETURN-CODE 等）
        #     同名（如 libgcobol compat 库的 LINKAGE 77 RETURN-CODE），符号表
        #     map 与引用解析需优先用户声明、覆盖预定义寄存器，避免
        #     "not a unique reference" / "RETURNING not in LINKAGE SECTION"。
        symfind_cc = os.path.join(src, "gcc", "cobol", "symfind.cc")
        if os.path.isfile(symfind_cc):
            with open(symfind_cc, "r", errors="surrogateescape") as f:
                t = f.read()
            old = (
                "  std::transform( symbols_begin(beg), symbols_end(),\n"
                "                  std::inserter(symbol_map, symbol_map.begin()),\n"
                "                  field_structure );\n"
                "  beg = end;\n"
            )
            new = (
                "  // Overwrite semantics: a user-declared field (added later)\n"
                "  // overrides a predefined global register (e.g. RETURN-CODE).\n"
                "  for( auto it = symbols_begin(beg); it != symbols_end(); ++it ) {\n"
                "    auto fs = field_structure(*it);\n"
                "    symbol_map[fs.first] = fs.second;\n"
                "  }\n"
                "  beg = end;\n"
            )
            t = t.replace(old, new, 1)
            old2 = (
                "bool\n"
                "update_symbol_map( symbol_elem_t *e ) {\n"
                "  auto output = symbol_map.insert(field_structure(*e));\n"
                "  return  output.second;\n"
                "}\n"
            )
            new2 = (
                "bool\n"
                "update_symbol_map( symbol_elem_t *e ) {\n"
                "  auto fs = field_structure(*e);\n"
                "  // Overwrite semantics: a user-declared field overrides a\n"
                "  // predefined global register of the same name.\n"
                "  symbol_map[fs.first] = fs.second;\n"
                "  return true;\n"
                "}\n"
            )
            t = t.replace(old2, new2, 1)
            old3 = (
                "  for( auto isym : matched ) {\n"
                "    auto e = symbol_at(isym);\n"
                "    auto f = cbl_field_of(e);\n"
                "\n"
                "    symbol_map_t::key_type key( e->program, f->name, f->parent );\n"
            )
            new3 = (
                "  for( auto isym : matched ) {\n"
                "    auto e = symbol_at(isym);\n"
                "    auto f = cbl_field_of(e);\n"
                "\n"
                "    // Prefer a user-declared field over a predefined global\n"
                "    // register of the same name (e.g. RETURN-CODE).\n"
                "    if( f->has_attr(global_e) ) {\n"
                "      bool has_local = false;\n"
                "      for( auto jsym : matched ) {\n"
                "        auto je = symbol_at(jsym);\n"
                "        auto jf = cbl_field_of(je);\n"
                "        if( je->program == e->program\n"
                "            && !jf->has_attr(global_e)\n"
                "            && 0 == strcasecmp(jf->name, f->name) ) {\n"
                "          has_local = true;\n"
                "          break;\n"
                "        }\n"
                "      }\n"
                "      if( has_local ) continue;\n"
                "    }\n"
                "\n"
                "    symbol_map_t::key_type key( e->program, f->name, f->parent );\n"
            )
            t = t.replace(old3, new3, 1)
            with open(symfind_cc, "w", errors="surrogateescape") as f:
                f.write(t)

    def _libxml2_dirs(self):
        dep = self.dependencies["libxml2"]
        pkg = dep.package_folder
        inc = os.path.join(pkg, "include", "libxml2")
        lib = os.path.join(pkg, "lib")
        return inc, lib

    @property
    def _toolchain_env(self):
        return (
            "AR=/data/service/hnp/bin/llvm-ar NM=/data/service/hnp/bin/llvm-nm "
            "RANLIB=/data/service/hnp/bin/llvm-ranlib STRIP=/data/service/hnp/bin/llvm-strip "
            "OBJCOPY=/data/service/hnp/bin/llvm-objcopy "
            "READELF=/data/service/hnp/bin/llvm-readelf LD=/data/service/hnp/bin/ld.lld "
            "CC=/data/service/hnp/bin/clang CXX=/data/service/hnp/bin/clang++ "
            "CC_FOR_BUILD=/data/service/hnp/bin/clang "
            "CXX_FOR_BUILD=/data/service/hnp/bin/clang++ "
            # 真机重启后 HMDFS 上 bash getcwd 失败，用 /bin/sh 作 CONFIG_SHELL。
            "CONFIG_SHELL=/bin/sh SHELL=/bin/sh "
            # config.status 的 mktemp 临时目录与 make -jN jobserver 的 mkfifo
            # 命名管道都建在 TMPDIR 下；HMDFS（/storage/.../.cache/tmp）上
            # subs1.awk 创建报 Permission denied（E011/E052/E060），必须指到
            # tmpfs（/data/storage/el2/base/cache）。configure 阶段虽已内联
            # TMPDIR，但 make all-gcc 触发的各子目录 configure 继承 make 进程
            # 环境，必须在这里一并固定 TMPDIR。
            "TMPDIR=/data/storage/el2/base/cache "
            # -fPIC: stderr 等 libc 符号 copy relocation 到 .bss 时 4 字节对齐，
            # clang 非 PIC 的 LDST64 绝对寻址触发 lld 对齐检查失败；走 GOT 规避。
            # -mstrict-align: aarch64 上 GCC 源码含 packed struct，生成对齐安全代码。
            "CFLAGS=\"-g -O2 -fPIC -mstrict-align\" "
            "CXXFLAGS=\"-g -O2 -fPIC -mstrict-align\" "
            "PATH=/data/service/hnp/bin:$PATH"
        )

    def generate(self):
        """生成自定义构建环境脚本（不用 conan 保留名 conanbuild，见 gcc-ada）。"""
        from conan.tools.env import Environment
        env = Environment()
        env.define("AR", "/data/service/hnp/bin/llvm-ar")
        env.define("NM", "/data/service/hnp/bin/llvm-nm")
        env.define("RANLIB", "/data/service/hnp/bin/llvm-ranlib")
        env.define("STRIP", "/data/service/hnp/bin/llvm-strip")
        env.define("OBJCOPY", "/data/service/hnp/bin/llvm-objcopy")
        env.define("READELF", "/data/service/hnp/bin/llvm-readelf")
        env.define("LD", "/data/service/hnp/bin/ld.lld")
        env.define("CC", "/data/service/hnp/bin/clang")
        env.define("CXX", "/data/service/hnp/bin/clang++")
        env.define("CC_FOR_BUILD", "/data/service/hnp/bin/clang")
        env.define("CXX_FOR_BUILD", "/data/service/hnp/bin/clang++")
        env.define("CONFIG_SHELL", "/bin/sh")
        env.define("SHELL", "/bin/sh")
        env.define("CFLAGS", "-g -O2 -fPIC -mstrict-align")
        env.define("CXXFLAGS", "-g -O2 -fPIC -mstrict-align")
        env.prepend_path("PATH", "/data/service/hnp/bin")
        env.vars(self).save_script("gcobol_build_env")

    def build(self):
        configure = os.path.join(self.source_folder, "configure")
        src = self.source_folder

        # _patch_ohos_sources() 已移到 source() 末尾（见 source 方法注释）。

        tmpdir = self._tmpdir
        os.makedirs(tmpdir, exist_ok=True)

        build_dir = os.path.join(self.build_folder, "obj")
        os.makedirs(build_dir, exist_ok=True)

        # 1. configure
        self.run(
            "cd {0} && export {1} && mkdir -p {2} && "
            "TMPDIR={2} /bin/sh {3} {4}".format(
                build_dir, self._toolchain_env, tmpdir, configure,
                " ".join(self._configure_args())),
            env="gcobol_build_env",
        )

        # PICFLAG 由 configure 的 --enable-host-shared 设为 -fPIC（见
        # _configure_args）；tm.h 的 insn-flags.h include 由 GCC 16 的
        # configure 自动生成（实测 gcc/tm.h 已含），无需再 patch 生成物。
        # 注意：gcc/Makefile 与 gcc/tm.h 都是 make all-gcc 触发 configure-gcc
        # 时才生成的，在顶层 configure 之后、make 之前 patch 它们时机太早，
        # 文件尚不存在，patch 会静默失效——这正是之前 improper alignment 的
        # 根因，已改用官方 configure 选项解决。

        # CI worker 资源/内存紧张（多 agent 共享），完整 GCC 构建 -j8 易触发
        # OOM / 资源竞争导致 all-gcc 失败；降到 -j4 更稳（真机 20 核仍可 -j8，
        # 但 CI 无此条件）。构建时长仍远小于 14400s CI 窗口。
        jobs = max(1, min(build_jobs(self), 4))

        # 2. all-gcc（cobol1 + gcobol 驱动 + cc1）
        #    ulimit -s unlimited：GCC 的 gen* 代码生成器 / cobol1 编译时递归
        #    深、栈需求大，CI worker 默认栈上限（8MB）会栈溢出/段错误导致
        #    all-gcc Error 2；真机手动构建（gcobol_manual_make.sh）正是靠
        #    这一步成功。
        self.run(
            "ulimit -s unlimited && export {0} && make -C {1} -j{2} all-gcc".format(
                self._toolchain_env, build_dir, jobs),
            env="gcobol_build_env",
        )

        # 删除 GCC 的 as/ld/nm/collect-ld 包装脚本（HMDFS 无 exec 位，xgcc
        # posix_spawn 直接执行失败），xgcc 退回用 hnp 的 GNU as/ld/nm。
        for name in ("as", "collect-ld", "nm"):
            p = os.path.join(build_dir, "gcc", name)
            if os.path.exists(p):
                os.remove(p)

        # 3. all-target-libgcc（顶层 target 库，用 xgcc 编译）
        #    移除 libstdc++-v3（gcobol 不需要 C++ 标准库，且其 configure 会
        #    "cannot run C compiled programs" 失败）。
        top_mk = os.path.join(build_dir, "Makefile")
        with open(top_mk, "r", errors="surrogateescape") as f:
            t = f.read()
        t = t.replace(
            "TARGET_CONFIGDIRS =  libgcc libstdc++-v3 libgcobol",
            "TARGET_CONFIGDIRS =  libgcc libgcobol",
        )
        t = t.replace(
            "    maybe-configure-target-libstdc++-v3 \\\n",
            "",
        )
        with open(top_mk, "w", errors="surrogateescape") as f:
            f.write(t)

        target = self._target_triplet
        sysr = self._ohos_sysroot
        xgcc = os.path.join(build_dir, "gcc", "xgcc")
        # GCC 16 的 cc1 不认识 OHOS 系统头文件里的 clang 扩展属性
        # __availability__（stdio.h 里 __attribute__((__availability__(ohos,
        # introduced=12.0.0))) 会被 cc1 解析成表达式 → 'introduced' undeclared /
        # 'too many decimal points in number'，导致 all-target-libgcc 编译
        # _muldi3.o 失败）。用 -include 一个兼容头把 __availability__(...)
        # 定义为空（真机手动构建的 ohos-compat.h 同款）。
        compat_h = os.path.join(build_dir, "ohos-compat.h")
        with open(compat_h, "w") as f:
            f.write("/* GCC compatibility: ignore Clang's __availability__ attribute. */\n")
            f.write("#define __availability__(...)\n")
        xgcc_args = (
            "-B{0}/gcc/ -B/data/service/hnp/bin/ "
            "-B{1}/usr/lib/{2}/ -isystem {1}/usr/include/{2} "
            "-isystem {1}/usr/include --sysroot={1} "
            "-include {3}".format(build_dir, sysr, target, compat_h)
        )
        cc_for_target = "{} {}".format(xgcc, xgcc_args)
        self.run(
            "ulimit -s unlimited && export {0} && make -C {1} -j{2} all-target-libgcc "
            "CC_FOR_TARGET=\"{3}\" "
            "CFLAGS_FOR_TARGET=\"-g -O2 -fPIC -D__OHOS__\"".format(
                self._toolchain_env, build_dir, jobs, cc_for_target),
            env="gcobol_build_env",
        )

        # 4. libgcobol：gcobol 构建无 cc1plus，libgcobol 是 C++ 库 → 用 OHOS
        #    clang++ 手动 configure+make（参考 libgcobol 单独适配 PR #11888）。
        self._build_libgcobol()

    def _build_libgcobol(self):
        src = os.path.join(self.source_folder, "libgcobol")
        build = os.path.join(self.build_folder, "obj", "aarch64-linux-ohos", "libgcobol")
        os.makedirs(build, exist_ok=True)
        sysr = self._ohos_sysroot
        libcxx = os.path.join(self._ohos_llvm, "include", "libcxx-ohos", "include", "c++", "v1")
        xml2_inc, xml2_lib = self._libxml2_dirs()

        clang = "/data/service/hnp/bin/clang"
        clangxx = "/data/service/hnp/bin/clang++"
        cc = "{} --sysroot={}".format(clang, sysr)
        cxx = "{} --sysroot={} -nostdinc++ -I{} -I{}".format(clangxx, sysr, libcxx, xml2_inc)
        cxxcpp = "{} --sysroot={} -E -nostdinc++ -I{} -I{}".format(clangxx, sysr, libcxx, xml2_inc)

        toolchain = (
            "AR=/data/service/hnp/bin/llvm-ar NM=/data/service/hnp/bin/llvm-nm "
            "RANLIB=/data/service/hnp/bin/llvm-ranlib LD=/data/service/hnp/bin/ld.lld "
            "PATH=/data/service/hnp/bin:$PATH"
        )

        self.run(
            "cd {0} && export {1} && TMPDIR={2} /bin/sh {3} "
            "--prefix=/ --build=aarch64-unknown-linux-musl "
            "--host=aarch64-unknown-linux-musl "
            "--disable-multilib --disable-libquadmath "
            "--with-target-libxml2-include={4} --with-target-libxml2-lib={5} "
            "CC='{6}' CXX='{7}' CXXCPP='{8}' "
            "CFLAGS='-g -O2 -fPIC' CXXFLAGS='-g -O2 -fPIC -Wno-null-character'".format(
                build, toolchain, self._tmpdir, os.path.join(src, "configure"),
                xml2_inc, xml2_lib, cc, cxx, cxxcpp),
            env="gcobol_build_env",
        )
        self.run(
            "export {0} && TMPDIR={6} make -C {1} -j{2} CC='{3}' CXX='{4}' "
            "CFLAGS='-g -O2 -fPIC' CXXFLAGS='-g -O2 -fPIC -Wno-null-character' "
            "LDFLAGS='-L{5} -lxml2' LIBS='-lclang_rt.builtins'".format(
                toolchain, build, max(1, min(build_jobs(self), 8)),
                cc, cxx, xml2_lib, self._tmpdir),
            env="gcobol_build_env",
        )

    @staticmethod
    def _required_executable(name, *candidates):
        for candidate in candidates:
            if not candidate:
                continue
            resolved = shutil.which(candidate)
            if not resolved and os.path.isfile(candidate) and os.access(
                    candidate, os.X_OK):
                resolved = os.path.abspath(candidate)
            if resolved:
                return resolved
        raise ConanInvalidConfiguration(
            "Required executable was not found: {}".format(name))

    def _sign_elf_tree(self, root):
        """OHOS 动态链接器只加载带 .codesign 的 ELF（EXEC/DYN）。"""
        signer = self._required_executable(
            "binary-sign-tool", "binary-sign-tool",
            "/data/service/hnp/bin/binary-sign-tool")
        objcopy = self._required_executable(
            "llvm-objcopy", "llvm-objcopy",
            "/data/service/hnp/bin/llvm-objcopy")
        readelf = self._required_executable(
            "llvm-readelf", "llvm-readelf",
            "/data/service/hnp/bin/llvm-readelf")

        for candidate in Path(root).rglob("*"):
            if not candidate.is_file() or candidate.is_symlink():
                continue
            probe = subprocess.run(
                [readelf, "-h", str(candidate)],
                capture_output=True, text=True)
            if probe.returncode != 0:
                continue
            # 已签名则跳过
            secs = subprocess.run(
                [readelf, "-S", str(candidate)],
                capture_output=True, text=True)
            if ".codesign" in secs.stdout:
                continue
            if not re.search(r"Type:\s+(?:EXEC|DYN)\b", probe.stdout):
                continue
            original_mode = stat.S_IMODE(candidate.stat().st_mode)
            unsigned = str(candidate) + ".ohos-unsigned"
            signed = str(candidate) + ".ohos-signed"
            shutil.copy2(str(candidate), unsigned)
            subprocess.run(
                [objcopy, "--remove-section", ".codesign", unsigned],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                check=False)
            subprocess.run(
                [signer, "sign", "-inFile", unsigned, "-outFile", signed,
                 "-selfSign", "1"], check=True)
            if ".codesign" not in subprocess.run(
                    [readelf, "-S", signed],
                    capture_output=True, text=True).stdout:
                raise ConanException(
                    "Signing did not add .codesign: {}".format(candidate))
            os.replace(signed, str(candidate))
            try:
                os.remove(unsigned)
            except OSError:
                pass
            os.chmod(str(candidate), original_mode | stat.S_IXUSR
                     | stat.S_IXGRP | stat.S_IXOTH)

    def _install_ohos_driver_wrapper(self):
        """把 DESTDIR 安装的 gcobol 驱动改造成可重定位 + OHOS 适配 wrapper。

        给每次 gcobol 调用加：
          - GCC_EXEC_PREFIX 重定位
          - -B$sysroot/usr/lib/$target/（crt1.o/crti.o/crtn.o、libc）
          - -B$package/lib/gcc/$target/$version/（libgcc、crtbegin/crtend）
          - -mmusl（切动态链接器到 /lib/ld-musl-aarch64.so.1）
          - -D__availability__(...)=（OHOS 头用 clang availability 语法）
          - -isystem $sysroot/usr/include/$target
        """
        bindir = Path(self.package_folder) / "bin"
        driver = bindir / "gcobol"
        real_driver = bindir / "gcobol.real"
        if not driver.is_file():
            raise ConanInvalidConfiguration(
                "The installed gcobol driver was not found: {}".format(driver))
        os.replace(driver, real_driver)

        target = self._target_triplet
        version = "16.1.0"  # GCC 上游版本（BASE-VER）
        sysroot = self._ohos_sysroot
        signer = self._required_executable(
            "binary-sign-tool", "binary-sign-tool",
            "/data/service/hnp/bin/binary-sign-tool")
        objcopy = self._required_executable(
            "llvm-objcopy", "llvm-objcopy",
            "/data/service/hnp/bin/llvm-objcopy")
        readelf = self._required_executable(
            "llvm-readelf", "llvm-readelf",
            "/data/service/hnp/bin/llvm-readelf")
        wrapper = """#!/bin/sh
set -eu

driver_path=$(readlink -f "$0")
package_root=$(CDPATH= cd "$(dirname "$driver_path")/.." && pwd -P)
real_driver="$package_root/bin/gcobol.real"
target={target}
version={version}
sysroot={sysroot}
signer={signer}
objcopy={objcopy}
readelf={readelf}

export GCC_EXEC_PREFIX="$package_root/libexec/gcc/"

set -- -mmusl "$@"
set -- -isystem "$sysroot/usr/include/$target" "$@"
set -- "-B$sysroot/usr/lib/$target/" "$@"
set -- "-B$package_root/lib/gcc/$target/$version/" "$@"
set -- "-L$package_root/lib/" "$@"

"$real_driver" "$@"

# 解析 -o 输出；若是链接出的 ELF，补 .codesign（OHOS 动态链接器只加载
# 已签名的 ELF）。-c/-S/-E 只编译无链接输出，跳过。
output=""
previous=""
compile_only=0
for argument in "$@"; do
    if [ "$previous" = "-o" ]; then
        output="$argument"
        previous=""
        continue
    fi
    case "$argument" in
        -o) previous="-o" ;;
        -o?*) output="${{argument#-o}}" ;;
        -c|-S|-E) compile_only=1 ;;
    esac
done

if [ "$compile_only" -eq 0 ] && [ -n "$output" ] && [ -f "$output" ]; then
    if "$readelf" -h "$output" 2>/dev/null | grep -Eq 'Type:[[:space:]]+(EXEC|DYN)'; then
        if ! "$readelf" -S "$output" 2>/dev/null | grep -q '[.]codesign'; then
            unsigned="${{output}}.ohos-unsigned-$$"
            signed="${{output}}.ohos-signed-$$"
            cp -p "$output" "$unsigned"
            "$objcopy" --remove-section .codesign "$unsigned" 2>/dev/null || true
            "$signer" sign -inFile "$unsigned" -outFile "$signed" -selfSign 1
            mv "$signed" "$output"
            rm -f "$unsigned"
            chmod +x "$output" 2>/dev/null || true
        fi
    fi
fi
exit 0
""".format(
            target=shlex.quote(target),
            version=shlex.quote(version),
            sysroot=shlex.quote(sysroot),
            signer=shlex.quote(signer),
            objcopy=shlex.quote(objcopy),
            readelf=shlex.quote(readelf),
        )
        driver.write_text(wrapper, encoding="utf-8")
        driver.chmod(
            driver.stat().st_mode | stat.S_IXUSR
            | stat.S_IXGRP | stat.S_IXOTH)

    def package(self):
        build_dir = os.path.join(self.build_folder, "obj")
        self.run(
            "make -C {0} install-gcc install-target-libgcc DESTDIR={1}".format(
                build_dir, self.package_folder),
            env="gcobol_build_env",
        )
        # libgcobol 是手动构建，其 install 未打进顶层 make；手动安装其产物。
        lgc_build = os.path.join(build_dir, "aarch64-linux-ohos", "libgcobol")
        libdir = os.path.join(self.package_folder, "lib")
        os.makedirs(libdir, exist_ok=True)
        for name in ("libgcobol.so", "libgcobol.so.2", "libgcobol.so.2.0.0",
                     "libgcobol.a"):
            src = os.path.join(lgc_build, ".libs", name)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(libdir, name))
        # libgcobol.spec 在 libgcobol 构建目录根，不在 .libs。
        spec_src = os.path.join(lgc_build, "libgcobol.spec")
        if os.path.isfile(spec_src):
            shutil.copy2(spec_src, os.path.join(libdir, "libgcobol.spec"))
            # 同时放到 lib/gcc/$target/$version/（-B 会搜 spec）
            gccverdir = os.path.join(
                self.package_folder, "lib", "gcc", self._target_triplet, "16.1.0")
            os.makedirs(gccverdir, exist_ok=True)
            shutil.copy2(spec_src, os.path.join(gccverdir, "libgcobol.spec"))

        # 清理 libtool .la（烤死绝对路径）
        import glob as _glob
        for la in _glob.glob(os.path.join(self.package_folder, "**", "*.la"),
                             recursive=True):
            os.remove(la)

        # 安装 OHOS 驱动 wrapper（加 -mmusl/-B/-isystem）
        self._install_ohos_driver_wrapper()

        # 对 package 内所有 ELF 签名（.so + 可执行）
        self._sign_elf_tree(self.package_folder)

    def package_info(self):
        self.cpp_info.bindirs = ["bin", "libexec"]
        # libgcobol.so 安装在 lib/，运行时 test_package 需要 LD_LIBRARY_PATH。
        self.cpp_info.libdirs = ["lib"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
