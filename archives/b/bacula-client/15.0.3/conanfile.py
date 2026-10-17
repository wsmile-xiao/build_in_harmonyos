#!/usr/bin/env python3
"""Conan recipe for bacula-client 15.0.3 on HarmonyOS (OHOS) aarch64.

Bacula is an open-source backup suite. bacula-client packages the
Bacula CLIENT toolset (interactive console + standalone client utility
tools) built from src/console/ + src/tools/. Same source tarball and
build chain as the merged-in precedent bacula-fd 15.0.3 (its OHOS
workaround chain is reused: non-HMDFS work dir + E007 --build +
env-quoted configure + forced HAVE_LIBZ undef + find_one.c FS-macros
patch + line-located binflate.c zlib stub).

Built components (build order):
  src/lib      libbac.so + libbaccfg.so   (base libs)
  src/findlib  libbacfind.so              (find engine, needed by
                                           fstype/drivetype/testls/testfind/bjoblist)
  src/cats     libbacsql.so + libbaccats.so (catalog libs, needed by
  9 DIRTOOLS; the 3 DB tools dbcheck/bbatch/bvfs_test are excluded)
                                           dbcheck/bbatch/bvfs_test -
                                           built WITHOUT a database backend)
  src/console  bconsole                   (interactive console; readline
                                           NOT used - conio.c/dumb fallback)
  src/tools    12 DIRTOOLS: bsmtp dbcheck drivetype fstype testfind
                 testls bregex bwild bbatch bregtest bvfs_test bjoblist
The dird-dependent tools (dbcheck/testfind/bbatch/bvfs_test) compile
4 dird conf objects in-place (src/tools/Makefile.in L148-155) -
bacula-dir itself is NOT built.

Deps: openssl/3.5.6 + zlib/1.3.1 (Bacula common, published on ohpcd).
readline is intentionally NOT a dependency (conio.c provides the
terminal fallback when curses/readline are absent).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get


class BaculaClientConan(ConanFile):
    name = "bacula-client"
    version = "15.0.3"
    package_type = "application"
    license = "AGPL-3.0"
    homepage = "https://www.bacula.org"
    url = "https://www.bacula.org"
    description = ("Bacula backup suite - client toolset (bconsole "
                   "interactive console + 12 standalone client tools "
                   "from src/tools, built from src/console + src/tools)")
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires("openssl/3.5.6")
        self.requires("zlib/1.3.1")

    def source(self):
        get(self, **self.conan_data["sources"][self.version],
            strip_root=True)
        # findlib/find_one.c: OHOS 的 <linux/fs.h> 缺 FS_IOC_GETFLAGS /
        # FS_NODUMP_FL 宏，且 include 在 #if HAVE_LINUX_OS && HAVE_NODUMP
        # 条件块内 - 无条件在文件顶部插入宏定义（#ifndef 保护；注意不能用
        # 'FS_NODUMP_FL not in fs' 判断 - 使用处本身就含该字符串，patch
        # 永不执行 - 用 startswith 标记防重复）。**client 也构建 src/findlib**
        # （libbacfind 供 fstype/drivetype/testls/testfind/bjoblist 用），
        # 先例 bacula-fd 同款 patch 原样保留
        ff = os.path.join(self.source_folder, "src", "findlib",
                          "find_one.c")
        fs = open(ff).read()
        macro_def = """/* OHOS patch: linux/fs.h lacks FS flags macros */
#ifndef FS_NODUMP_FL
#define FS_NODUMP_FL 0x00000040
#endif
#ifndef FS_IOC_GETFLAGS
#define FS_IOC_GETFLAGS _IOR('f', 129, long)
#endif
"""
        if not fs.startswith("/* OHOS patch"):
            open(ff, "w").write(macro_def + fs)
            print("find_one.c FS flags macros patched (top, forced)")
        # src/lib/binflate.c: --disable-zlib 后仍无条件编译 zlib 代码
        # (#include <zlib.h> + Zdeflate/Zinflate 用 deflate/inflate -
        # 链接 libbac.so 时引用非 PIC zlib 的 z_errmsg 符号 -> R_AARCH64
        # 重定位失败; --disable-zlib 只影响 config.h 不影响此文件) -
        # 行号定位替换 Zdeflate/Zinflate 函数体为压缩禁用 stub (不引用
        # zlib 符号, 调用方对返回 0/out_len=0 走无压缩路径)。
        # 注意: 先例 guard 为 len(blines) > 103; 本 tarball 的 binflate.c
        # 恰好 103 行 (含末尾换行), guard 不触发 - 实际排除 zlib 靠下面
        # build() 里强制 undef HAVE_LIBZ (binflate.c 的 zlib 代码都在
        # #ifdef HAVE_LIBZ 内)。stub 逻辑原样保留先例 (对 >103 行的
        # 源码树仍生效, 双重保险)
        bf = os.path.join(self.source_folder, "src", "lib", "binflate.c")
        blines = open(bf).readlines()
        stub = [
            "/* OHOS --disable-zlib: compression disabled (patched) */\n",
            "int Zdeflate(char *in, int in_len, char *out, int &out_len) {\n",
            "    out_len = 0;\n",
            "    return 0;\n",
            "}\n",
            "int Zinflate(char *in, int in_len, char *out, int &out_len) {\n",
            "    out_len = 0;\n",
            "    return 0;\n",
            "}\n",
        ]
        # 26 行 (#include <zlib.h>) 到 103 行 (Zinflate 结束 }) 替换为 stub
        if len(blines) > 103 and "zlib.h" in blines[25]:
            open(bf, "w").writelines(blines[:25] + stub + blines[103:])
            print("binflate.c zlib compression stubbed")
        # OHOS musl libc 无 getpass() (sysroot 头文件无原型, libc.so 无符号)
        # - console.c:401 (HAVE_TLS 分支) 与 authenticate.c:189 (非 WIN32
        # 分支, 无条件活跃) 都调用, 且 bacula 全部 .c 用 CXX 编译 (C++ 隐式
        # 声明是硬错误) -> 必须提供原型 + 实现。原型进 bacula.h (两个调用
        # 文件都 include); 实现放新文件 src/console/ohos_getpass.c (termios
        # 无回显最小实现), build() 里注入 console Makefile 的 CONSOBJS
        bh = os.path.join(self.source_folder, "src", "bacula.h")
        bt = open(bh).read()
        if "/* OHOS getpass shim */" not in bt:
            bt += (
                "\n/* OHOS getpass shim */\n"
                "char *getpass(const char *prompt);\n"
            )
            open(bh, "w").write(bt)
            print("bacula.h getpass prototype appended")
        # getpass 实现直接追加进 console.c (console.o 必在 CONSOBJS 首位,
        # bconsole 必链接到它; authenticate.o 的调用在链接期解析到这里的
        # 定义). 不走 Makefile 编辑: build() 期改生成 Makefile 可能被
        # config.status 自重新生成规则洗掉. 链接错误显示 mangled
        # getpass(char const*) 证明无 extern "C" 守卫, 追加定义同 C++
        # linkage, 符号必然匹配. 变量名 ohos_gp_ 前缀防与 console.c 既有
        # 符号 (c/i/oldt 等) 冲突
        cc_file = os.path.join(self.source_folder, "src", "console",
                               "console.c")
        cctxt = open(cc_file).read()
        if "OHOS getpass definition" not in cctxt:
            cctxt += (
                "\n/* OHOS getpass definition (musl libc has no getpass) */\n"
                "#include <stdio.h>\n"
                "#include <termios.h>\n"
                "static char ohos_gp_buf[256];\n"
                "char *getpass(const char *prompt)\n"
                "{\n"
                "    struct termios ohos_gp_oldt, ohos_gp_newt;\n"
                "    char ohos_gp_c;\n"
                "    int ohos_gp_i = 0;\n"
                "    int ohos_gp_echoed = (tcgetattr(0, &ohos_gp_oldt) != 0);\n"
                "    if (!ohos_gp_echoed) {\n"
                "        ohos_gp_newt = ohos_gp_oldt;\n"
                "        ohos_gp_newt.c_lflag &= ~ECHO;\n"
                "        tcsetattr(0, TCSAFLUSH, &ohos_gp_newt);\n"
                "    }\n"
                "    if (prompt) { fprintf(stderr, \"%s\", prompt); }\n"
                "    while ((ohos_gp_c = getchar()) != '\\n' &&\n"
                "           ohos_gp_c != EOF) {\n"
                "        if (ohos_gp_i < 255) {\n"
                "            ohos_gp_buf[ohos_gp_i++] = ohos_gp_c;\n"
                "        }\n"
                "    }\n"
                "    ohos_gp_buf[ohos_gp_i] = '\\0';\n"
                "    if (!ohos_gp_echoed) {\n"
                "        tcsetattr(0, TCSAFLUSH, &ohos_gp_oldt);\n"
                "    }\n"
                "    if (prompt) { fprintf(stderr, \"\\n\"); }\n"
                "    return ohos_gp_buf;\n"
                "}\n"
            )
            open(cc_file, "w").write(cctxt)
            print("console.c getpass definition appended")

    def build(self):
        openssl = self.dependencies["openssl"]
        zlib = self.dependencies["zlib"]
        # E011 根治 (先例 bacula-fd/bacula-pgsql 同款实证): config.status
        # 在当前目录生成并直接执行 ./confXXXX/subs1.awk (HMDFS 执行位被
        # 剥) - 源码复制到非 HMDFS (/data/storage/el2/base/cache) 再
        # configure/make。work 路径带唯一后缀 (与 bacula-fd 的
        # bacula-fd-src-3 区分, 避免旧副本残留污染目录权限 - 实测
        # 'getcwd: cannot access parent directories: Permission denied')
        work = "/data/storage/el2/base/cache/bacula-client-src-3"
        shutil.rmtree(work, ignore_errors=True)
        shutil.copytree(self.source_folder, work, symlinks=True)
        # el2 沙箱目录权限: copytree 创建的子目录 owner/权限可能异常,
        # findlib 子目录递归 cd 时 getcwd 报 'cannot access parent
        # directories: Permission denied' - 构建前递归放开 work 目录权限
        os.system(f"chmod -R 777 {work}")
        # env 引号 + E007 --build; bacula 15.0.3 configure 要求至少指定
        # --enable-client-only 或一个数据库后端 (db_backends 为空则
        # 'This is not permitted' 中止) - client 是纯客户端组件 ->
        # --enable-client-only 通过。readline 不引: 不加 --with-readline,
        # configure 找不到 readline.h 自动关闭, console 走 conio.c/dumb
        # 终端回退 (不依赖 readline/curses 包)
        # CC/CXX 显式注入: 本机 conan 2.29.1 buildenv 只给 CONFIG_SHELL/
        # SHELL/PATH (无 CC/CXX) -> configure 'no acceptable C compiler
        # found in $PATH'. 从 profile conf tools.build:compiler_executables
        # 取值 (CI/本地 profile 均已配置), 缺省回退 cc/c++
        ccx = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cc = ccx.get("c", "cc")
        cxx = ccx.get("cpp", "c++")
        self.run(
            f"env CC=\"{cc}\" CXX=\"{cxx}\" "
            f"CPPFLAGS=\"-I{openssl.package_folder}/include "
            f"-I{zlib.package_folder}/include\" "
            f"LDFLAGS=\"-L{openssl.package_folder}/lib "
            f"-L{zlib.package_folder}/lib\" "
            f"./configure --build=aarch64-unknown-linux-gnu "
            f"--prefix={self.package_folder} --enable-client-only "
            "--disable-zlib",
            cwd=work,
        )
        # --disable-zlib 未让 config.h 的 HAVE_LIBZ undef (zlib 头/库检测
        # 通过 - 实测仍 #define HAVE_LIBZ 1) -> binflate.c 的 zlib 代码
        # (#ifdef HAVE_LIBZ 条件编译) 被编译 -> libbac.so 链接引用非 PIC
        # zlib 的 z_errmsg -> R_AARCH64 重定位失败。**强制 undef HAVE_LIBZ**
        # (利用已有条件编译 - zlib 代码被排除, libbac 无 zlib 引用)
        cfg_path = os.path.join(work, "src", "config.h")
        cfg = open(cfg_path).read()
        cfg = cfg.replace("#define HAVE_LIBZ 1", "/* #undef HAVE_LIBZ */")
        open(cfg_path, "w").write(cfg)
        print("config.h HAVE_LIBZ forced undef (disable zlib)")
        # src/tools/Makefile: DIRTOOLS (12 工具) 依赖 dird 对象 -
        # configure 默认 build_dird=yes (--enable-client-only 不改它,
        # 见 configure L22226-22253) -> DIR_TOOLS=DIRTOOLS 已生效, 无需
        # 改 TOOLS。仅做校验: 若生成结果不是 $(DIRTOOLS) (上游改默认
        # 值), dbcheck/testfind/bbatch/bvfs_test 会因缺 dird 对象而
        # 链接失败 - 这里明确报错而非静默漏工具
        ttools = os.path.join(work, "src", "tools", "Makefile")
        tmk = open(ttools).read()
        if "TOOLS = $(DIRTOOLS)" not in tmk:
            raise RuntimeError(
                "src/tools/Makefile DIR_TOOLS 非 DIRTOOLS (预期 12 工具, "
                "实际可能为 NODIRTOOLS) - 请确认 configure 仍默认 "
                "build_dird=yes; 若上游改默认值需显式 --enable-build-dird")
        print("tools Makefile DIR_TOOLS=DIRTOOLS verified (12 tools)")
        # dbcheck/bbatch/bvfs_test 链接 -lbaccats -lbacsql (catalog DB 层);
        # client-only 无 DB 后端, catalog 层符号 (db_int64_handler,
        # BDB::bdb_get_engine_name 等) 缺失, 永远无法链接。与上游 Debian
        # bacula-client (metapackage, Depends: bacula-console + bacula-fd)
        # 语义一致: client 不含 DB 一致性工具。TOOLS 改写为显式 9 工具
        tmk2 = open(ttools).read()
        if "TOOLS = $(DIRTOOLS)" in tmk2:
            tmk2 = tmk2.replace(
                "TOOLS = $(DIRTOOLS)",
                "TOOLS = bsmtp drivetype fstype testfind testls "
                "bregex bwild bregtest bjoblist", 1)
            open(ttools, "w").write(tmk2)
            print("tools Makefile TOOLS: 3 DB tools removed "
                  "(dbcheck bbatch bvfs_test)")
        # build the client components only - 依赖链 (逐个先构建, 实测
        # findlib 报 'No rule to make target ../lib/libbac.la'):
        #   src/lib      libbac/libbaccfg (一切基础)
        #   src/findlib  libbacfind (fstype/drivetype/testls/testfind/bjoblist)
        #   src/cats     libbacsql/libbaccats (dbcheck/bbatch/bvfs_test,
        #                 无数据库后端 - cats all 只构建两个 .la)
        #   src/console  bconsole
        #   src/tools    12 DIRTOOLS (dird conf 对象在 tools 内就地编译)
        self.run("make -C src/lib", cwd=work)
        self.run("make -C src/findlib", cwd=work)
        # cats Makefile: 无 DB 后端时 all 目标引用 libbaccats-none.la 但
        # 该目标无构建规则 (configure 假设至少一个 DB 后端) -> make 报
        # 'No rule to make target libbaccats-none.la'. tools 实际只链接
        # libbacsql + libbaccats, 从 all: 行删掉幽灵依赖
        cats_mk = os.path.join(work, "src", "cats", "Makefile")
        mktxt = open(cats_mk).read()
        if "libbaccats-none.la" in mktxt:
            mktxt = mktxt.replace("libbaccats-none.la", "").replace(
                "  ", " ")
            open(cats_mk, "w").write(mktxt)
            print("cats Makefile: libbaccats-none.la removed from all")
        self.run("make -C src/cats", cwd=work)
        self.run("make -C src/console", cwd=work)
        # tools 的 testfind 链接守护进程 conf 对象 (../dird/*.o);
        # client-only 模式不构建 daemon, 先用 dird Makefile 自带的 .c.o
        # 隐式规则预编译这 4 个纯 conf .o (不含 daemon main, 只依赖已
        # 构建的 libbac). ../stored/*.o 只被 test-dedup 链接, 而
        # all: $(TOOLS) gigaslam grow 的 TOOLS=DIRTOOLS 12 工具不含
        # test-dedup, 故无需 stored 对象
        self.run(
            "make -C src/dird dird_conf.o inc_conf.o run_conf.o ua_acl.o",
            cwd=work)
        self.run("make -C src/tools", cwd=work)

    def package(self):
        # 产物在非 HMDFS 构建目录 (work) - build() 把源码复制到
        # /data/storage/el2/base/cache/bacula-client-src-3 构建 (E011 方案)
        work = "/data/storage/el2/base/cache/bacula-client-src-3"
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        # libtool 链接: 可执行落在 <dir>/ (包装脚本) 或 <dir>/.libs/ (实体
        # 二进制, static 或 use_libtool=no 时无 .libs) - 两种布局都兜底
        def _copy_tool(src_dir, tool):
            cand = os.path.join(src_dir, ".libs", tool)
            if not os.path.exists(cand):
                cand = os.path.join(src_dir, tool)
            if not os.path.exists(cand):
                raise RuntimeError(f"{tool} not found under {src_dir}")
            shutil.copy2(cand, os.path.join(bin_dir, tool))

        # bconsole (src/console)
        _copy_tool(os.path.join(work, "src", "console"), "bconsole")
        # 9 DIRTOOLS (src/tools) - dbcheck/bbatch/bvfs_test 剔除 (DB 工具,
        # client-only 无 catalog DB 后端无法链接, 见 build() 注释)
        for t in ("bsmtp", "drivetype", "fstype", "testfind",
                  "testls", "bregex", "bwild", "bregtest",
                  "bjoblist"):
            _copy_tool(os.path.join(work, "src", "tools"), t)
        # libtool 共享库: bin 下 10 个工具全部链接 libbac/libbaccfg/
        # libbacfind (RUNPATH 已由 toolchain 指向 <pkg>/lib) - 不打包则
        # 运行时 127 "Error loading shared library libbac-15.0.3.so"
        lib_dir = os.path.join(self.package_folder, "lib")
        os.makedirs(lib_dir, exist_ok=True)
        for so in ("libbac-%s.so" % self.version,
                   "libbaccfg-%s.so" % self.version):
            shutil.copy2(os.path.join(work, "src", "lib", ".libs", so),
                         os.path.join(lib_dir, so))
        shutil.copy2(os.path.join(work, "src", "findlib", ".libs",
                                  "libbacfind-%s.so" % self.version),
                     os.path.join(lib_dir, "libbacfind-%s.so" % self.version))
        # license
        shutil.copy2(os.path.join(self.source_folder, "COPYING"),
                     os.path.join(self.package_folder, "COPYING"))

    def package_info(self):
        # client 主要是 bin 工具 (无 lib/include 导出) - 按先例 bacula-fd
        # 模式暴露主可执行路径 (bconsole); 12 个 tools 在 <pkg>/bin/
        self.conf_info.define("user.bacula-client:exe", os.path.join(
            self.package_folder, "bin", "bconsole"))
