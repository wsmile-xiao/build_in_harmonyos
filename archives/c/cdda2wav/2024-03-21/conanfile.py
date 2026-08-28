#!/usr/bin/env python3
"""Conan recipe for cdda2wav 2024-03-21 — CD 音频抓取工具（C）。

cdda2wav 是 schilytools 套件（Schily Tools，C 语言）的 cdda2wav
成员（CD 音频抓取工具，依赖 libparanoia）。版本 2024-03-21 为
schilytools 上游 tag（用户给 1.0.0 不合法——按真实版 2024-03-21）。

Upstream: https://codeload.github.com/clausecker/schilytools/tar.gz/refs/tags/2024-03-21

Build:   schilytools 自研 smake 构建（顶层 make 构建 psmake + smake
         后构建所有工具含 cdda2wav）。依赖 scg（SCSI 接口）+ schily
         基础库 + libparanoia——套件内自包含，无需外部 Conan 包。
Install: bin/cdda2wav（make install 装 bin + man）。
Type:   application（CLI 工具——commands.json 软件级声明）

上游测试: schilytools 无独立测试目录（cdda2wav 是音频抓取工具，运行
         需光驱/SCSI 设备——OHOS 无，如实记录）。
"""
import os

from conan import ConanFile
from conan.tools.files import get
from conan.tools.layout import basic_layout


class Cdda2wavConan(ConanFile):
    name = "cdda2wav"
    version = "2024-03-21"
    description = "CD audio grabber (schilytools, cdda2wav)"
    license = "GPL-2.0"
    homepage = "https://sourceforge.net/projects/schilytools/"
    url = "https://github.com/clausecker/schilytools"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    # schilytools 自包含构建（scg + schily 基础库套件内自带）——无外部依赖

    def layout(self):
        basic_layout(self)

    def source(self):
        # codeload URL 含 /tar.gz/ 段——conan get() 误判 zip（BadZipFile，
        # batsignal/c4project 同款），显式 filename
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="schilytools-2024-03-21.tar.gz")

    def build(self):
        # schilytools psmake configure 的 AC_CHECK_DFUNC/AC_CHECK_FUNCS
        # 检查（ac_link 编译测试程序）在 OHOS 上普遍卡死（卡死点随机：
        # dirfd/clock_settime/pthread/thr_yield 等）——patch 生成源
        # autoconf/configure.in，一次性跳过所有 AC_CHECK_DFUNC/AC_CHECK_FUNCS
        # 检查（configure 是构建时从 configure.in 生成的）
        import re
        # schilytools 构建时 srcroot=..（psmake 上级 = build 目录）——
        # configure 从 build 目录的 autoconf/configure.in 生成，patch 它
        cfg_in = os.path.join(self.build_folder, "autoconf", "configure.in")
        if not os.path.isfile(cfg_in):
            # fallback：source 目录（若 build 目录无）
            cfg_in = os.path.join(self.source_folder, "autoconf", "configure.in")
        with open(cfg_in, "r", encoding="utf-8", errors="replace") as f:
            s = f.read()
        # 跳过所有 AC_CHECK_DFUNC/AC_CHECK_FUNCS/AC_CHECK_LIB（ac_link
        # 编译测试程序在 OHOS 上卡死）
        s2 = re.sub(r'AC_CHECK_DFUNC\(.*?\)', 'dnl AC_CHECK_DFUNC(...)  # skipped: hangs on OHOS',
                    s, flags=re.DOTALL)
        s2 = re.sub(r'AC_CHECK_FUNCS\([^)]*\)',
                    r'dnl AC_CHECK_FUNCS(...)  # skipped: hangs on OHOS', s2)
        s2 = re.sub(r'AC_CHECK_LIB\([^)]*\)',
                    r'dnl AC_CHECK_LIB(...)  # skipped: hangs on OHOS', s2)
        # 跳过 AC_CHECK_LIB(c, pthread_create)（多行形式，re.sub 不匹配时兜底）
        s2 = s2.replace(
            "AC_CHECK_LIB(c, pthread_create, lib_pthread=\"\",\n"
            "  [AC_CHECK_LIB(pthread, pthread_create, lib_pthread=\"-lpthread\")])",
            "dnl AC_CHECK_LIB(c, pthread_create, ...)  # skipped: hangs on OHOS")
        if s2 != s:
            with open(cfg_in, "w", encoding="utf-8") as f:
                f.write(s2)
        # schilytools 源码自带旧版 autoconf/configure（MAKE-sh 只在 configure
        # 缺失时才从 configure.in 重新生成）——patch configure 本身（source +
        # build 两个目录都 patch，确保构建用的那份生效），跳过所有 ac_link
        # 编译测试和 ./conftest 运行测试（OHOS 上卡死）
        for cfg in (os.path.join(self.build_folder, "autoconf", "configure"),
                    os.path.join(self.source_folder, "autoconf", "configure")):
            if not os.path.isfile(cfg):
                continue
            with open(cfg, "r", encoding="utf-8", errors="replace") as f:
                sc = f.read()
            # 保护 cc 检查的 ac_link（后跟 ac_cv_prog_cc_works——需要真实
            # 编译验证编译器可用），只替换其他检查的编译测试
            cc_link = ("eval $ac_link ;} 2>&5; } && test -s conftest${ac_exeext};"
                       " then\n  ac_cv_prog_cc_works=yes")
            sc2 = sc.replace(cc_link, "@@CC_LINK@@")
            # 跳过其他检查的 ac_link 编译测试：eval $ac_link（编译 conftest
            # 测试程序，OHOS 上卡死）替换为直接设置 ac_cv_x=yes
            sc2 = sc2.replace("eval $ac_link", "eval ac_cv_x=yes")
            sc2 = sc2.replace("@@CC_LINK@@", cc_link)
            # 跳过运行测试程序：./conftest 运行测试在 OHOS 上卡死——true
            # （不破坏 configure 脚本结构，re.sub cat > conftest 会破坏
            # if/else 结构导致 syntax error，已弃用）
            sc2 = sc2.replace("./conftest", "true")
            if sc2 != sc:
                with open(cfg, "w", encoding="utf-8") as f:
                    f.write(sc2)
        # schilytools libport.h 的 usleep 声明（extern int usleep(int)）与
        # OHOS unistd.h 的 int usleep(unsigned) 签名冲突（configure 检查被
        # 跳过致 HAVE_USLEEP 未定义）——patch 声明为 unsigned 与 OHOS 一致
        for lp in (os.path.join(self.build_folder, "include", "schily",
                                "libport.h"),
                   os.path.join(self.source_folder, "include", "schily",
                                "libport.h")):
            if not os.path.isfile(lp):
                continue
            with open(lp, "r", encoding="utf-8", errors="replace") as f:
                sc = f.read()
            sc2 = sc.replace("extern\tint\t\tusleep\t\t__PR((int usec));",
                             "extern\tint\t\tusleep\t\t__PR((unsigned usec));")
            if sc2 != sc:
                with open(lp, "w", encoding="utf-8") as f:
                    f.write(sc2)
        # schilytools 把 fexecve 重定义为 js_fexecve（schily.h）与 OHOS
        # unistd.h 的 fexecve 声明冲突（conflicting types）——注释掉重定义，
        # 用 OHOS libc 的系统 fexecve
        for sh in (os.path.join(self.build_folder, "include", "schily",
                                "schily.h"),
                   os.path.join(self.source_folder, "include", "schily",
                                "schily.h")):
            if not os.path.isfile(sh):
                continue
            with open(sh, "r", encoding="utf-8", errors="replace") as f:
                sc = f.read()
            sc2 = sc.replace("#define\tfexecve\t\tjs_fexecve",
                             "/* #define\tfexecve\t\tjs_fexecve */")
            if sc2 != sc:
                with open(sh, "w", encoding="utf-8") as f:
                    f.write(sc2)
        # schilytools hostname.h 的 gethostname 声明与 OHOS unistd.h 冲突
        # （conflicting types）——patch 跳过（OHOS libc 已有 gethostname）
        for hn in (os.path.join(self.build_folder, "include", "schily",
                                "hostname.h"),
                   os.path.join(self.source_folder, "include", "schily",
                                "hostname.h")):
            if not os.path.isfile(hn):
                continue
            with open(hn, "r", encoding="utf-8", errors="replace") as f:
                sc = f.read()
            sc2 = sc.replace("#ifndef\tHAVE_GETHOSTNAME",
                             "#if 0  /* HAVE_GETHOSTNAME skipped */")
            if sc2 != sc:
                with open(hn, "w", encoding="utf-8") as f:
                    f.write(sc2)
        # hostname.h 的 getdomainname 声明与 OHOS unistd.h 冲突——跳过
        for hn in (os.path.join(self.build_folder, "include", "schily",
                                "hostname.h"),
                   os.path.join(self.source_folder, "include", "schily",
                                "hostname.h")):
            if not os.path.isfile(hn):
                continue
            with open(hn, "r", encoding="utf-8", errors="replace") as f:
                sc = f.read()
            sc2 = sc.replace("#ifndef\tHAVE_GETDOMAINNAME",
                             "#if 0  /* HAVE_GETDOMAINNAME skipped */")
            if sc2 != sc:
                with open(hn, "w", encoding="utf-8") as f:
                    f.write(sc2)
        # varargs.h 的 __va_arg_list：VA_LIST_IS_ARRAY 被 configure 误判
        # 致 va_arg(list, void*) 传 void* 给 va_list（libc++ 严格类型报错）
        # ——强制用 va_arg(list, va_list)（OHOS libc++ va_list 非数组）
        for vh in (os.path.join(self.build_folder, "include", "schily",
                                "varargs.h"),
                   os.path.join(self.source_folder, "include", "schily",
                                "varargs.h")):
            if not os.path.isfile(vh):
                continue
            with open(vh, "r", encoding="utf-8", errors="replace") as f:
                sc = f.read()
            sc2 = sc.replace(
                "#ifdef\tVA_LIST_IS_ARRAY\n#\tdefine\t__va_arg_list(list)\tva_arg(list, void *)\n#else\n#\tdefine\t__va_arg_list(list)\tva_arg(list, va_list)\n#endif",
                "#define\t__va_arg_list(list)\tva_arg(list, va_list)  /* OHOS libc++ va_list */")
            if sc2 != sc:
                with open(vh, "w", encoding="utf-8") as f:
                    f.write(sc2)
        # psmake/job.c 的 Exit 未声明（system() 分支）——局部声明；
        # psmake/job.c 是软链接（-> ../smake/job.c），glob 找所有 job.c
        # 真实文件 + 宽松替换（不限定缩进）
        import glob as _g
        for jc in set(_g.glob(os.path.join(self.build_folder, "**", "job.c"),
                              recursive=True)) | \
                  set(_g.glob(os.path.join(self.source_folder, "**", "job.c"),
                              recursive=True)):
            if not os.path.isfile(jc):
                continue
            with open(jc, "r", encoding="utf-8", errors="replace") as f:
                sc = f.read()
            sc2 = sc.replace("Exit = system(cmd);",
                             "int Exit = system(cmd);")
            if sc2 != sc:
                with open(jc, "w", encoding="utf-8") as f:
                    f.write(sc2)
        # getcwd.h：HAVE_GETCWD 未定义（configure 检查被跳过）致 getcwd 被
        # 重定义为 getwd（OHOS libc 无 getwd）——glob 找所有 getcwd.h
        # （include/ 与 psmake/include/ 两份）跳过重定义用系统 getcwd
        for gc in set(_g.glob(os.path.join(self.build_folder, "**",
                                           "schily", "getcwd.h"),
                              recursive=True)) | \
                  set(_g.glob(os.path.join(self.source_folder, "**",
                                           "schily", "getcwd.h"),
                              recursive=True)):
            if not os.path.isfile(gc):
                continue
            with open(gc, "r", encoding="utf-8", errors="replace") as f:
                sc = f.read()
            sc2 = sc.replace("#\tifndef\tHAVE_GETCWD",
                             "#\tif 0  /* HAVE_GETCWD skipped: use system getcwd */")
            if sc2 != sc:
                with open(gc, "w", encoding="utf-8") as f:
                    f.write(sc2)
        # comerr.c：sys_nerr/sys_errlist（旧 glibc 全局变量）OHOS musl 无——
        # 用 strerror(err) 替代
        for cc in (os.path.join(self.build_folder, "libschily", "comerr.c"),
                   os.path.join(self.source_folder, "libschily", "comerr.c")):
            if not os.path.isfile(cc):
                continue
            with open(cc, "r", encoding="utf-8", errors="replace") as f:
                sc = f.read()
            sc2 = sc.replace(
                "\tif (err < 0 || err >= sys_nerr) {\n\t\treturn (NULL);\n\t} else {\n\t\treturn (sys_errlist[err]);\n\t}",
                "\treturn (strerror(err));")
            if sc2 != sc:
                with open(cc, "w", encoding="utf-8") as f:
                    f.write(sc2)
        # serrmsg.c：HAVE_STRERROR 未定义致声明 sys_errlist/sys_nerr（OHOS
        # musl 无）——跳过声明
        for sm in (os.path.join(self.build_folder, "libschily", "serrmsg.c"),
                   os.path.join(self.source_folder, "libschily", "serrmsg.c")):
            if not os.path.isfile(sm):
                continue
            with open(sm, "r", encoding="utf-8", errors="replace") as f:
                sc = f.read()
            sc2 = sc.replace("#ifndef\tHAVE_STRERROR",
                             "#if 0  /* HAVE_STRERROR skipped */")
            if sc2 != sc:
                with open(sm, "w", encoding="utf-8") as f:
                    f.write(sc2)
        # schilytools config.guess 不识 HarmonyOS（uname -s=HarmonyOS）致
        # host 系统类型检查失败（unknownCPU-unknownMFR-unknownOS）→ RULES
        # 用 unknown-cc（CC 失效）——patch fallback 识别 HarmonyOS 为
        # aarch64-unknown-linux-gnu
        for cg in (os.path.join(self.build_folder, "autoconf", "config.guess"),
                   os.path.join(self.source_folder, "autoconf", "config.guess")):
            if not os.path.isfile(cg):
                continue
            with open(cg, "r", encoding="utf-8", errors="replace") as f:
                sc = f.read()
            sc2 = sc.replace(
                "\techo unknownCPU-unknownMFR-unknownOS",
                '\tcase "${UNAME_SYSTEM}" in\n'
                '\t    HarmonyOS|harmonyos|ohos)\n'
                '\t\techo ${UNAME_MACHINE}-unknown-linux-gnu ;;\n'
                '\t    *)\n'
                '\t\techo unknownCPU-unknownMFR-unknownOS ;;\n'
                '\tesac')
            if sc2 != sc:
                with open(cg, "w", encoding="utf-8") as f:
                    f.write(sc2)
        # cc-config.sh 用 cc 默认编译器（OHOS 无 cc 命令只有 clang）致
        # RULES 配置 "using cc as default compiler" + cc 检查失败——patch
        # cc-config.sh 默认编译器为 clang
        for ccg in (os.path.join(self.build_folder, "conf", "cc-config.sh"),
                    os.path.join(self.source_folder, "conf", "cc-config.sh")):
            if not os.path.isfile(ccg):
                continue
            with open(ccg, "r", encoding="utf-8", errors="replace") as f:
                sc = f.read()
            # 默认编译器 cc → clang（OHOS 无 cc，只有 clang）——强制
            # CC/DEF_CC 为 clang（schilytools 调用传 cc）
            sc2 = sc.replace("CC=$1\t\t\t# Working copy of discovered C-compiler",
                             "CC=clang\t\t# OHOS: no cc, only clang")
            sc2 = sc2.replace("DEF_CC=$2\t\t# Name of default C-compiler",
                              "DEF_CC=clang\t# OHOS: no cc, only clang")
            if sc2 != sc:
                with open(ccg, "w", encoding="utf-8") as f:
                    f.write(sc2)
        # rules1.top 的 DEFCCOM_DEF= cc（schilytools 默认编译器）——OHOS 无
        # cc 命令只有 clang，patch 默认编译器为 clang
        for rt in (os.path.join(self.build_folder, "RULES", "rules1.top"),
                   os.path.join(self.source_folder, "RULES", "rules1.top")):
            if not os.path.isfile(rt):
                continue
            with open(rt, "r", encoding="utf-8", errors="replace") as f:
                sc = f.read()
            sc2 = sc.replace("DEFCCOM_DEF=\tcc",
                             "DEFCCOM_DEF=\tclang  # OHOS: no cc, only clang")
            if sc2 != sc:
                with open(rt, "w", encoding="utf-8") as f:
                    f.write(sc2)
        # configure 的 cc 检测：ac_cv_prog_CC 失败时默认 cc/gcc（OHOS 无
        # cc/gcc 命令只有 clang）——patch 所有 configure 强制 clang
        import glob as _g2
        # 注意：glob **/configure 可能不匹配顶层 configure（schilytools
        # 构建用顶层 configure，未 patch 会卡死 strchr 等检查）——显式加
        _cfg_dirs = set(_g2.glob(os.path.join(self.build_folder, "**",
                                              "configure"), recursive=True)) | \
                    set(_g2.glob(os.path.join(self.source_folder, "**",
                                              "configure"), recursive=True))
        for _c in (os.path.join(self.build_folder, "configure"),
                   os.path.join(self.source_folder, "configure")):
            _cfg_dirs.add(_c)
        for cf2 in _cfg_dirs:
            if not os.path.isfile(cf2):
                continue
            with open(cf2, "r", encoding="utf-8", errors="replace") as f:
                sc = f.read()
            # 全面替换 cc/gcc 默认编译器为 clang（re.sub，覆盖所有文本形式）
            sc2 = re.sub(r'ac_cv_prog_CC="(cc|gcc)"',
                         'ac_cv_prog_CC="clang"  # OHOS', sc)
            sc2 = re.sub(r'ac_cv_prog_CC="(cc|gcc)";?',
                         'ac_cv_prog_CC="clang"  # OHOS', sc2)
            sc2 = re.sub(r'test -z "\$ac_cv_prog_CC" && ac_cv_prog_CC="(cc|gcc)"',
                         'test -z "$ac_cv_prog_CC" && ac_cv_prog_CC="clang"', sc2)
            # 检测的编译器命令名 cc/gcc → clang（AC_CHECK_PROG(CC, cc, cc, gcc)
            # 生成的 set dummy cc；ac_word 是检测命令名）
            sc2 = re.sub(r'set dummy cc; ac_word=\$2',
                         'set dummy clang; ac_word=$2  # OHOS', sc2)
            sc2 = re.sub(r'set dummy gcc; ac_word=\$2',
                         'set dummy clang; ac_word=$2  # OHOS', sc2)
            sc2 = re.sub(r'set dummy cc;', 'set dummy clang;  # OHOS', sc2)
            sc2 = re.sub(r'set dummy gcc;', 'set dummy clang;  # OHOS', sc2)
            # 类型/头文件检查（int16_t 等）用 ac_compile 编译 conftest 在
            # OHOS 上卡死（eval $ac_link patch 不覆盖编译测试）——跳过
            sc2 = re.sub(r'eval \$ac_compile ;?\} 2>&5; \} && test -s conftest',
                         'eval ac_cv_x=yes; } && test -s conftest', sc2)
            # ac_link 测试的运行步骤（$rmtcall 远程运行测试，mlockall 等
            # 检查在 OHOS 上卡死）——跳过运行（直接成功）
            sc2 = re.sub(r'\(\$rmtcall true\$\{ac_xexeext\}; exit\) 2>/dev/null',
                         '(exit 0) 2>/dev/null  # OHOS: skip run test', sc2)
            # 所有 for ac_func in ... 函数检查循环 → dummy 列表 _skip_all
            # （跳过全部函数检查——schilytools 各 configure 副本的函数检查
            # 在 OHOS 上连环卡死：getspnam/accessat/getenv/signal/strchr/
            # timegm 等）。注意原行可能是 "for ac_func in a b c; do"（分号
            # +do 同行），若替换成空列表注释会把 "; do" 吃掉，下一行 echo
            # 成孤儿 → syntax error（create63 教训）——必须保留 ; do 结构
            sc2 = re.sub(r'for ac_func in [^\n]*$',
                         lambda m: 'for ac_func in _skip_all'
                         + ('; do' if m.group(0).rstrip().endswith('; do') else '')
                         + '  # all funcs skipped: hangs on OHOS',
                         sc2, flags=re.MULTILINE)
            # accessat/mkdirat 等 *at 函数检查在 OHOS 上卡死——跳过
            sc2 = re.sub(r'for ac_func in __accessat$',
                         'for ac_func in  # __accessat skipped: hangs on OHOS', sc2, flags=re.MULTILINE)
            sc2 = re.sub(r'for ac_func in accessat$',
                         'for ac_func in  # accessat skipped: hangs on OHOS', sc2, flags=re.MULTILINE)
            sc2 = re.sub(r'for ac_func in mkdirat faccessat fchmodat linkat mkfifoat mknodat readlinkat symlinkat$',
                         'for ac_func in  # *at skipped: hangs on OHOS', sc2, flags=re.MULTILINE)
            # getenv/putenv/setenv/unsetenv 函数检查在 OHOS 上卡死——跳过
            sc2 = re.sub(r'for ac_func in getenv putenv setenv unsetenv$',
                         'for ac_func in  # getenv etc skipped: hangs on OHOS', sc2, flags=re.MULTILINE)
            # 信号函数检查（signal/sighold/sigrelse 等）在 OHOS 上卡死——跳过
            sc2 = re.sub(r'for ac_func in signal sighold sigrelse sigignore sigpause sigprocmask sigsetmask sigset sigaltstack sigblock$',
                         'for ac_func in  # signal family skipped: hangs on OHOS', sc2, flags=re.MULTILINE)
            sc2 = re.sub(r'for ac_func in kill killpg$',
                         'for ac_func in  # kill family skipped: hangs on OHOS', sc2, flags=re.MULTILINE)
            # mmap/shmget 等运行测试程序检查（conftest 可执行，OHOS 上
            # open("/dev/zero") 等运行卡死）——cross_compiling 判断改为
            # 始终 true（走 no 分支，跳过运行测试程序）
            sc2 = re.sub(r'if test "\$cross_compiling" = yes; then',
                         'if test "$cross_compiling" = yes -o true; then  # OHOS: skip run tests', sc2)
            # AC_TRY_RUN 检查（cross_compiling 时报错退出）——替换报错为
            # 设置对应 ac_cv_* 缓存变量（跳过检查不退出）
            sc2 = sc2.replace(
                '{ echo "configure: error: can not run test program while cross compiling" 1>&2; exit 1; }',
                'ac_cv_dev_minor_bits=no; ac_cv_dev_minor_noncontig=no; ac_cv_wnowait_waitpid=no; :')
            # sizeof 检查（AC_CHECK_SIZEOF）：eval $ac_link patch 后 conftest
            # 不编译致 ac_cv_sizeof_* 空/0 → xconfig.h 的 SIZEOF_* 空值
            # （#if SIZEOF_MODE_T invalid token 根因）——默认值 aarch64 64 位
            for _sz, _def in (("char", 1), ("short_int", 2), ("int", 4),
                              ("long_int", 8), ("long_long", 8), ("__int64", 8),
                              ("char_p", 8), ("unsigned_char", 1),
                              ("unsigned_short_int", 2), ("unsigned_int", 4),
                              ("unsigned_long", 8), ("unsigned_long_int", 8),
                              ("unsigned_long_long", 8), ("unsigned___int", 4),
                              ("mode_t", 4), ("time_t", 8), ("off_t", 8),
                              ("size_t", 8), ("wchar", 4), ("wchar_t", 4),
                              ("ullong", 8), ("dev_t", 8)):
                sc2 = re.sub(r'ac_cv_sizeof_%s=0' % _sz,
                             'ac_cv_sizeof_%s=%d  # OHOS aarch64' % (_sz, _def),
                             sc2)
            sc2 = re.sub(r'ac_cv_sizeof_[a-z_0-9]+=0',
                         'ac_cv_sizeof_x=8  # OHOS aarch64 default', sc2)
            # config.status 生成的 sed 替换（ac_dB）把 #define NAME VALUE 的
            # 值丢弃（[^ 	]* 值无捕获组）→ xconfig.h 的 SIZEOF_* 空值
            # （#if SIZEOF_MODE_T invalid token 根因）——ac_dB 值加捕获组
            # + ac_dC 保留值
            sc2 = sc2.replace(
                "ac_dB='\\([ \t][ \t]*\\)[^ \t]*%\\1#\\2'",
                "ac_dB='\\([ \t][ \t]*\\)\\([^ \t]*\\)%\\1#\\2'  # OHOS keep value")
            sc2 = sc2.replace("ac_dC='\\3'",
                              "ac_dC='\\3\\4'  # OHOS keep value")
            # RETSIGTYPE（signal handler 返回类型）检查：ac_cv_type_signal=void
            # 写进 confdefs.h → config.status 模板 VALUE=void 非空，与 ac_dC
            # '\3\4' 保留值拼成 voidvoid（avoffset.c unknown type name 根因）。
            # 去值：模板 VALUE 变空，统一靠 \4 保留 xconfig.h.in 写死值
            sc2 = re.sub(r'#define RETSIGTYPE \$ac_cv_type_signal',
                         '#define RETSIGTYPE', sc2)
            if sc2 != sc:
                with open(cf2, "w", encoding="utf-8") as f:
                    f.write(sc2)
        # conf/makeinc 的 CC=cc（schilytools RULES 配置硬编码 cc，RULES
        # configure 的 "C compiler cc not found" 根因）——patch CC=clang
        for mi in (os.path.join(self.build_folder, "conf", "makeinc"),
                   os.path.join(self.source_folder, "conf", "makeinc")):
            if not os.path.isfile(mi):
                continue
            with open(mi, "r", encoding="utf-8", errors="replace") as f:
                sc = f.read()
            sc2 = sc.replace("CC=cc", "CC=clang  # OHOS: no cc, only clang")
            if sc2 != sc:
                with open(mi, "w", encoding="utf-8") as f:
                    f.write(sc2)
        # schilytools 全量构建 60+ 工具（bsh/ved/star/mkisofs 等）在 OHOS 上
        # 太慢（create69 290s 只编译到 libschily checkerr.o 就超时）——只
        # 保留 cdrecord + readcd 及其依赖库（15conf/25inc/43libschily/
        # 44libscg/45libedc 等），删除 Targets 里其余工具项
        _keep_targets = {"15conf", "25inc", "25include", "43libschily",
                         "44libdeflt", "44libscg", "44libscg!@!scg",
                         "44libxtermcap", "45lib", "45libcdrdeflt",
                         "45libdbgmalloc", "45libedc", "45libfile",
                         "45libfind", "45libgetopt", "45libhfs_iso",
                         "45libmdigest", "45libparanoia", "45librmt",
                         "45librscg", "45libscgcmd", "45libshedit",
                         "45libsiconv", "45libsiconv!@!tables",
                         "45libstreamar", "53smake", "55cdda2wav",
                         "85man"}
        for _td in (os.path.join(self.build_folder, "Targets"),
                    os.path.join(self.source_folder, "Targets")):
            if not os.path.isdir(_td):
                continue
            for _tf in os.listdir(_td):
                if _tf in _keep_targets or _tf.startswith(("README",
                                                           "Targetdirs",
                                                           "__slot")):
                    continue
                try:
                    os.remove(os.path.join(_td, _tf))
                except OSError:
                    pass
        # 依赖生成（MKDEP=clang -M）在 OHOS 上随机挂起（create64/65/66 卡在
        # fgetstr/matchl/rename.d 不同点——非固定文件问题）——一次性构建
        # 不需要增量 .d 依赖，patch 成创建空 .d（: > $@）跳过 clang -M
        for _rul in set(_g2.glob(os.path.join(self.build_folder, "RULES",
                                              "cc-*.rul"))) | \
                    set(_g2.glob(os.path.join(self.source_folder, "RULES",
                                              "cc-*.rul"))):
            if not os.path.isfile(_rul):
                continue
            with open(_rul, "r", encoding="utf-8", errors="replace") as f:
                sc = f.read()
            sc2 = sc.replace("$(CC_COM) $(CLANG_OPTXX) -M",
                             ": > $@")
            sc2 = sc2.replace("$(CC++_COM) $(CLANG_OPTXX) -M",
                              ": > $@")
            if sc2 != sc:
                with open(_rul, "w", encoding="utf-8") as f:
                    f.write(sc2)
        # xconfig.h 的 SIZEOF_* 宏（sizeof 检查被 eval $ac_link patch 跳过
        # 致未定义，make.h 的 #if SIZEOF_* invalid token）——patch 默认值
        # （aarch64 OHOS 64 位）
        sizeof_defs = (
            "\n/* OHOS aarch64 64-bit defaults (sizeof checks skipped) */\n"
            "#ifndef\tSIZEOF_CHAR\n#\tdefine\tSIZEOF_CHAR\t1\n#endif\n"
            "#ifndef\tSIZEOF_SHORT_INT\n#\tdefine\tSIZEOF_SHORT_INT\t2\n#endif\n"
            "#ifndef\tSIZEOF_INT\n#\tdefine\tSIZEOF_INT\t4\n#endif\n"
            "#ifndef\tSIZEOF_LONG\n#\tdefine\tSIZEOF_LONG\t8\n#endif\n"
            "#ifndef\tSIZEOF_LONG_INT\n#\tdefine\tSIZEOF_LONG_INT\t8\n#endif\n"
            "#ifndef\tSIZEOF_LONG_LONG\n#\tdefine\tSIZEOF_LONG_LONG\t8\n#endif\n"
            "#ifndef\tSIZEOF_LLONG\n#\tdefine\tSIZEOF_LLONG\t8\n#endif\n"
            "#ifndef\tSIZEOF_CHAR_P\n#\tdefine\tSIZEOF_CHAR_P\t8\n#endif\n"
            "#ifndef\tSIZEOF_UNSIGNED_CHAR\n#\tdefine\tSIZEOF_UNSIGNED_CHAR\t1\n#endif\n"
            "#ifndef\tSIZEOF_UNSIGNED_SHORT_INT\n#\tdefine\tSIZEOF_UNSIGNED_SHORT_INT\t2\n#endif\n"
            "#ifndef\tSIZEOF_UNSIGNED_INT\n#\tdefine\tSIZEOF_UNSIGNED_INT\t4\n#endif\n"
            "#ifndef\tSIZEOF_UNSIGNED_LONG\n#\tdefine\tSIZEOF_UNSIGNED_LONG\t8\n#endif\n"
            "#ifndef\tSIZEOF_UNSIGNED_LONG_INT\n"
            "#\tdefine\tSIZEOF_UNSIGNED_LONG_INT\t8\n#endif\n"
            "#ifndef\tSIZEOF_UNSIGNED_LONG_LONG\n"
            "#\tdefine\tSIZEOF_UNSIGNED_LONG_LONG\t8\n#endif\n"
            "#ifndef\tSIZEOF_UNSIGNED___INT\n#\tdefine\tSIZEOF_UNSIGNED___INT\t4\n#endif\n"
            "#ifndef\tSIZEOF_TIME_T\n#\tdefine\tSIZEOF_TIME_T\t8\n#endif\n"
            "#ifndef\tSIZEOF_ULLONG\n#\tdefine\tSIZEOF_ULLONG\t8\n#endif\n"
            "#ifndef\tSIZEOF_MODE_T\n#\tdefine\tSIZEOF_MODE_T\t4\n#endif\n"
            "#ifndef\tSIZEOF_WCHAR\n#\tdefine\tSIZEOF_WCHAR\t4\n#endif\n"
            "#ifndef\tSIZEOF_WCHAR_T\n#\tdefine\tSIZEOF_WCHAR_T\t4\n#endif\n")
        for xc in set(_g2.glob(os.path.join(self.build_folder, "**",
                                           "xconfig.h"),
                              recursive=True)) | \
                  set(_g2.glob(os.path.join(self.source_folder, "**",
                                            "xconfig.h"),
                               recursive=True)):
            if not os.path.isfile(xc):
                continue
            with open(xc, "r", encoding="utf-8", errors="replace") as f:
                sc = f.read()
            # 注意：configure 生成的空值 SIZEOF 宏也算"存在"，不能用
            # SIZEOF_UNSIGNED_LONG_INT 判断——用 OHOS 注释（sizeof_defs
            # 是否已插入）作条件
            if "OHOS aarch64" not in sc:
                # SIZEOF_* 定义必须放在 xconfig.h 开头（#ifndef 之后），
                # 因为 #if SIZEOF_* 判断（line 939 等）在文件前部——
                # 放末尾则判断时宏尚未定义（invalid token）。
                # 注意 xconfig.h 的 #ifndef 用空格非 tab——re.sub 匹配
                sc2 = re.sub(r'#ifndef[ \t]*_SCHILY_XCONFIG_H',
                             '#ifndef _SCHILY_XCONFIG_H' + sizeof_defs, sc, count=1)
                # configure 生成的 `#define SIZEOF_XXX `（空值）在后面
                # **覆盖** sizeof_defs 的默认值（#if SIZEOF_MODE_T invalid
                # token 根因）——删除空值 SIZEOF 定义行（保留开头默认值）
                sc2 = re.sub(r'^#define[ \t]+SIZEOF_[A-Z_]+[ \t]*\n',
                             '', sc2, flags=re.MULTILINE)
                with open(xc, "w", encoding="utf-8") as f:
                    f.write(sc2)
        # xconfig.h.in 模板的 #undef SIZEOF_* → #define SIZEOF_* 默认值
        # （config.status 生成 xconfig.h 时 SIZEOF_* 替换值空——ac_dC='\3'
        # 空——#if SIZEOF_MODE_T invalid token 根因）
        sizeof_map = {"CHAR": 1, "SHORT_INT": 2, "INT": 4, "LONG_INT": 8,
                      "LONG_LONG": 8, "LLONG": 8, "CHAR_P": 8,
                      "UNSIGNED_CHAR": 1, "UNSIGNED_SHORT_INT": 2,
                      "UNSIGNED_INT": 4, "UNSIGNED_LONG": 8,
                      "UNSIGNED_LONG_INT": 8, "UNSIGNED_LONG_LONG": 8,
                      "UNSIGNED___INT": 4, "TIME_T": 8, "ULLONG": 8,
                      "MODE_T": 4, "WCHAR": 4, "WCHAR_T": 4, "OFF_T": 8,
                      "SIZE_T": 8, "DEV_T": 8, "__INT64": 8}
        for xhi in set(_g2.glob(os.path.join(self.build_folder, "**",
                                             "xconfig.h.in"),
                                recursive=True)) | \
                   set(_g2.glob(os.path.join(self.source_folder, "**",
                                             "xconfig.h.in"),
                                recursive=True)):
            if not os.path.isfile(xhi):
                continue
            with open(xhi, "r", encoding="utf-8", errors="replace") as f:
                sc = f.read()
            sc2 = sc
            # 所有 #undef SIZEOF_* → #define SIZEOF_* 默认值（aarch64 64 位；
            # sizeof_map 查不到默认 8——ptr/长类型 8 字节）。注意 xconfig.h.in
            # 行尾常带注释（如 SIZEOF_WCHAR 后 /* sizeof (L'a') */），
            # [ \t]*$ 匹配不到——需吃掉尾部注释（SIZEOF_WCHAR 空值根因）
            def _szrepl(m):
                _sn = m.group(1)
                return '#define SIZEOF_%s %d' % (_sn, sizeof_map.get(_sn, 8))
            sc2 = re.sub(r'#undef[ \t]+SIZEOF_([A-Z0-9_]+)[ \t]*(?:/\*.*\*/)?[ \t]*$',
                         _szrepl, sc2, flags=re.MULTILINE)
            # RETSIGTYPE（signal handler 返回类型）：configure 检查写 confdefs.h
            # 的 #define RETSIGTYPE void 已被去值（模板 VALUE 空），此处把
            # #undef RETSIGTYPE 写死 #define RETSIGTYPE void（aarch64 通用）
            sc2 = re.sub(r'#undef[ \t]+RETSIGTYPE[ \t]*$',
                         '#define RETSIGTYPE void', sc2, flags=re.MULTILINE)
            # *at 系列函数（openat/fchmodat 等）：configure 的 for ac_func
            # 函数检查循环被跳过（OHOS 上卡死）→ HAVE_* 未定义 → fallback
            # 定义与 libport.h 声明冲突（fchmodat 3 参 vs 4 参 conflicting
            # types）——OHOS musl 真实存在这些 POSIX.1-2008 *at 函数，
            # 写死 #define HAVE_* 1（行尾常带注释，.*$ 吃掉整行）
            for _fn in ("OPENAT", "FSTATAT", "FCHOWNAT", "FUTIMESAT",
                        "RENAMEAT", "UNLINKAT", "MKDIRAT", "FACCESSAT",
                        "FCHMODAT", "LINKAT", "MKFIFOAT", "MKNODAT",
                        "READLINKAT", "SYMLINKAT"):
                sc2 = re.sub(r'#undef[ \t]+HAVE_%s.*$' % _fn,
                             '#define HAVE_%s 1' % _fn, sc2,
                             flags=re.MULTILINE)
            # wc 系列宽字符函数（wcscat/wcstol/iswctype/mbtowc 等）：同样
            # 因 for ac_func 检查被跳过而 HAVE_* 未定义 → libport.h/wctype.h
            # 的 fallback 声明与 musl wchar.h 冲突（fnmatch.c 19 errors：
            # conflicting types）——OHOS musl 全有，写死 #define HAVE_* 1
            for _fn in ("WCSCAT", "WCSNCAT", "WCSCMP", "WCSNCMP", "WCSCPY",
                        "WCSLCAT", "WCSLCPY", "WCSNCPY", "WCSDUP", "WCSNDUP",
                        "WCSLEN", "WCSNLEN", "WCSCHR", "WCSRCHR", "WCSSTR",
                        "WCSSPN", "WCSCSPN", "WCWIDTH", "WCSWIDTH", "WCTYPE",
                        "ISWCTYPE", "FGETWS", "WCSTOL", "WCSTOLL", "WCSTOUL",
                        "WCSTOULL", "ISWPRINT", "ISWBLANK", "ISBLANK",
                        "MBSINIT", "MBTOWC", "WCTOMB", "MBRTOWC", "WCRTOMB",
                        "GETHOSTNAME", "GETDOMAINNAME", "GETLINE",
                        "GETDELIM", "RAW_GETLINE", "RAW_FGETLINE",
                        "MEMMOVE", "STRCASECMP", "STRNCASECMP", "STRTOUL",
                        "STRTOLL", "STRTOULL"):
                sc2 = re.sub(r'#undef[ \t]+HAVE_%s.*$' % _fn,
                             '#define HAVE_%s 1' % _fn, sc2,
                             flags=re.MULTILINE)
            if sc2 != sc:
                with open(xhi, "w", encoding="utf-8") as f:
                    f.write(sc2)
        # config.status 的 sed 替换把 #define SIZEOF_* <值> 的值丢弃
        # （ac_dB 模式 `[^ 	]*` 值无捕获组）→ 生成的 xconfig.h 宏空值
        # ——patch config.status 的 ${ac_dC} 替换值为默认值
        for cs in set(_g2.glob(os.path.join(self.build_folder, "**",
                                            "config.status"),
                               recursive=True)) | \
                  set(_g2.glob(os.path.join(self.source_folder, "**",
                                            "config.status"),
                               recursive=True)):
            if not os.path.isfile(cs):
                continue
            with open(cs, "r", encoding="utf-8", errors="replace") as f:
                sc = f.read()
            sc2 = sc
            for _sn, _sd in sizeof_map.items():
                sc2 = re.sub(
                    r'\$\{ac_dA\}SIZEOF_%s\$\{ac_dB\}SIZEOF_%s\$\{ac_dC\}\$\{ac_dD\}' % (_sn, _sn),
                    '${ac_dA}SIZEOF_%s${ac_dB}SIZEOF_%s${ac_dC}%d${ac_dD}  # OHOS' % (_sn, _sn, _sd),
                    sc2)
            if sc2 != sc:
                with open(cs, "w", encoding="utf-8") as f:
                    f.write(sc2)
        # sndconfig.c 的 sun/audioio.h + sys/audioio.h 是 Solaris 专用音频头
        # （OHOS sysroot 无）——HAVE_SUN_AUDIOIO_H/HAVE_SYS_AUDIOIO_H 被
        # configure 误判定义（头文件检查在 OHOS 上不可靠）→ include 失败
        # （sndconfig.c fatal error）。禁用这两个 include（cdda2wav 的
        # sun/sys 音频输出在 OHOS 上不可用，走 /dev/dsp 即可）
        for sc2f in (os.path.join(self.build_folder, "cdda2wav",
                                  "sndconfig.c"),
                    os.path.join(self.source_folder, "cdda2wav",
                                 "sndconfig.c")):
            if not os.path.isfile(sc2f):
                continue
            with open(sc2f, "r", encoding="utf-8", errors="replace") as f:
                sc = f.read()
            s2 = sc.replace(
                "#ifdef\tHAVE_SUN_AUDIOIO_H\n# include <sun/audioio.h>\n#endif\n"
                "#ifdef\tHAVE_SYS_AUDIOIO_H\n# include <sys/audioio.h>\n#endif",
                "#if 0  /* OHOS: no sun/sys audioio.h (Solaris-only) */\n"
                "# include <sun/audioio.h>\n# include <sys/audioio.h>\n#endif")
            if s2 != sc:
                with open(sc2f, "w", encoding="utf-8") as f:
                    f.write(s2)
        # conf/install-sh 硬编码临时目录 /tmp/xd.$$（dstdir）——OHOS /tmp
        # 只读，make install 的 install-sh 报 "mkdir: '/tmp/xd.XXXX':
        # Read-only file system" 失败。patch 用 TMPDIR 环境变量（可写）
        # 或 build_folder 下的可写路径
        for isf in (os.path.join(self.build_folder, "conf", "install-sh"),
                    os.path.join(self.source_folder, "conf", "install-sh")):
            if not os.path.isfile(isf):
                continue
            with open(isf, "r", encoding="utf-8", errors="replace") as f:
                sc = f.read()
            s2 = sc.replace(
                "dstdir=/tmp/xd.$$",
                "dstdir=${TMPDIR:-/tmp}/xd.$$  # OHOS: /tmp read-only, use TMPDIR")
            if s2 != sc:
                with open(isf, "w", encoding="utf-8") as f:
                    f.write(s2)
        # schilytools 顶层 make：构建 psmake + smake 后构建所有工具
        # （含 cdrecord）。-j1 绕 OHOS 禁 mkfifo jobserver（catdoc/boa
        # 同款）。TMPDIR 指向可写目录——OHOS /tmp 只读，configure 的
        # ac_link 编译测试程序写 /tmp 失败/卡死（根因：cc 检查失败 +
        # 多个检查卡住的元凶）。export CC=clang + ac_cv_prog_cc=clang
        # 环境变量——OHOS 无 cc/gcc 命令只有 clang，schilytools 各
        # configure（psmake/RULES）默认 cc 致 "C compiler cc not found"
        self.run("cd %s && TMPDIR=%s && export CC=clang && "
                 "export ac_cv_prog_cc=clang && make -j1"
                 % (self.source_folder, self.build_folder), env="conanbuild")

    def package(self):
        # make install 装 bin/cdda2wav + man（DESTDIR 到 package）。
        # INS_BASE=/ —— schilytools 默认装 /opt/schily（DEFAULTS/Defaults.*
        # 的 INS_BASE=/opt/schily），消费测试期望 bin/cdda2wav。
        # TMPDIR 指向 build_folder——OHOS /tmp 只读，install-sh 的
        # 临时文件（/tmp/xd.xxxx）创建失败（mkdir: Read-only file system）
        self.run("cd %s && TMPDIR=%s && make install DESTDIR=%s "
                 "INS_BASE=/ -j1"
                 % (self.source_folder, self.build_folder,
                    self.package_folder), env="conanbuild")

    def package_info(self):
        self.output.info("cdda2wav 2024-03-21: bin/cdda2wav")
        self.conf_info.define("user.tools.cdda2wav:exe", "cdda2wav")
