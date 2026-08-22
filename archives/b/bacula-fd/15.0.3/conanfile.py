#!/usr/bin/env python3
"""Conan recipe for bacula-fd 15.0.3 on HarmonyOS PC.

Bacula is an open-source backup suite. bacula-fd packages the File
Daemon (backup client daemon) built from src/filed/. Same source
tarball and build chain as bacula-pgsql (already adapted — its 9-layer
OHOS fix chain is reused: non-HMDFS work dir + E007 --build + E011
subs1.awk + env-quoted configure).

Deps: openssl/3.5.6 + zlib/1.3.1 (Bacula common, published on ohpcd).
Runtime: fd connects to a Bacula Director (absent on OHOS) — real
operation not verifiable; test degrades to binary presence +
executable + ELF (honest, environment limitation).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get


class BaculaFdConan(ConanFile):
    name = "bacula-fd"
    version = "15.0.3"
    package_type = "application"
    license = "AGPL-3.0"
    homepage = "https://www.bacula.org"
    url = "https://www.bacula.org"
    description = ("Bacula backup suite — File Daemon (backup client "
                   "daemon, src/filed)")
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires("openssl/3.5.6")
        self.requires("zlib/1.3.1")

    def configure(self):
        # zlib 用 shared（.so 是 PIC）：静态非 PIC zlib 的 z_errmsg 符号在
        # 链接 libbac.so 时 R_AARCH64 重定位失败（capnproto 同款
        # 'recompile with -fPIC'）——shared zlib 可正常重定位。
        # 依赖 options 必须在 configure() 设置（requirements() 里设报
        # 'Dependencies options were defined incorrectly'）
        self.options["zlib"].shared = True

    def source(self):
        get(self, **self.conan_data["sources"][self.version],
            strip_root=True)
        # findlib/find_one.c: OHOS 的 <linux/fs.h> 缺 FS_IOC_GETFLAGS /
        # FS_NODUMP_FL 宏，且 include 在 #if HAVE_LINUX_OS && HAVE_NODUMP
        # 条件块内（HAVE_NODUMP 未定义 → include 被跳过）——无条件在文件
        # 顶部插入宏定义（#ifndef 保护；注意不能用 'FS_NODUMP_FL not in
        # fs' 判断——使用处本身就含该字符串，patch 永不执行——用
        # startswith 标记防重复）
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
        # （#include <zlib.h> + Zdeflate/Zinflate 用 deflate/inflate——
        # 链接 libbac.so 时引用非 PIC zlib 的 z_errmsg 符号 → R_AARCH64
        # 重定位失败；--disable-zlib 只影响 config.h 不影响此文件）——
        # 行号定位替换 Zdeflate/Zinflate 函数体为压缩禁用 stub（不引用
        # zlib 符号，调用方对返回 0/out_len=0 走无压缩路径）
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
        # 26 行（#include <zlib.h>）到 103 行（Zinflate 结束 }）替换为 stub
        if len(blines) > 103 and "zlib.h" in blines[25]:
            open(bf, "w").writelines(blines[:25] + stub + blines[103:])
            print("binflate.c zlib compression stubbed")
        # src/filed/bxattr.c: OHOS 无 xattr 支持（sys/xattr.h 不存在实测
        # ——llistxattr/lgetxattr 头缺失）→ bxattr.o 未编译 → filed 链接
        # undefined new_bxattr/BXATTR::backup_xattr/restore_xattr。
        # **替换为 stub**（返回 bRC_BXATTR_error——xattr 不支持，如实说明）
        bx = os.path.join(self.source_folder, "src", "filed", "bxattr.c")
        stub_bxattr = '''// OHOS: no xattr support — stub (patched by recipe)
#include "bacula.h"
#include "fd_plugins.h"
struct FF_PKT; /* forward decl — FF_PKT defined inside conditional
                  blocks (skipped on OHOS); must precede bxattr.h */
#include "bxattr.h"
BXATTR::BXATTR() {}
BXATTR::~BXATTR() {}
bRC_BXATTR BXATTR::backup_xattr(JCR *jcr, FF_PKT *ff_pkt) { return bRC_BXATTR_error; }
bRC_BXATTR BXATTR::restore_xattr(JCR *jcr, int stream, char *content, unsigned int content_length) { return bRC_BXATTR_error; }
bRC_BXATTR BXATTR::generic_backup_xattr(JCR *jcr, FF_PKT *ff_pkt) { return bRC_BXATTR_error; }
bRC_BXATTR BXATTR::generic_restore_xattr(JCR *jcr, int stream) { return bRC_BXATTR_error; }
bRC_BXATTR BXATTR::gpfs_backup_xattr(JCR *jcr, FF_PKT *ff_pkt) { return bRC_BXATTR_error; }
bRC_BXATTR BXATTR::gpfs_restore_xattr(JCR *jcr, int stream) { return bRC_BXATTR_error; }
void *new_bxattr() { return NULL; }
'''
        open(bx, "w").write(stub_bxattr)
        print("bxattr.c stubbed (no xattr on OHOS)")

    def build(self):
        openssl = self.dependencies["openssl"]
        zlib = self.dependencies["zlib"]
        # E011 根治（bacula-pgsql 同款实证）：config.status 在当前目录生成
        # 并直接执行 ./confXXXX/subs1.awk（HMDFS 执行位被剥）——源码复制到
        # 非 HMDFS（/data/storage/el2/base/cache）再 configure/make。
        # work 路径带唯一后缀（旧副本残留可能污染目录权限——实测
        # 'getcwd: cannot access parent directories: Permission denied'）
        work = "/data/storage/el2/base/cache/bacula-fd-src-3"
        shutil.rmtree(work, ignore_errors=True)
        shutil.copytree(self.source_folder, work, symlinks=True)
        # el2 沙箱目录权限：copytree 创建的子目录 owner/权限可能异常，
        # findlib 子目录递归 cd 时 getcwd 报 'cannot access parent
        # directories: Permission denied'（bacula-pgsql 的 src/cats 无
        # 子目录递归未触发；perl-xml-libxml 曾用 chmod 0o777 修同款）
        # ——构建前递归放开 work 目录权限
        os.system(f"chmod -R 777 {work}")
        # env 引号 + E007 --build；bacula 15.0.3 configure 要求至少指定
        # --enable-client-only 或一个数据库后端（db_backends 为空则
        # 'This is not permitted' 中止——bacula-pgsql 用 --with-postgresql
        # 通过；fd 是纯客户端组件 → --enable-client-only 只构建客户端）
        self.run(
            f"env CPPFLAGS=\"-I{openssl.package_folder}/include "
            f"-I{zlib.package_folder}/include\" "
            f"LDFLAGS=\"-L{openssl.package_folder}/lib "
            f"-L{zlib.package_folder}/lib\" "
            f"./configure --build=aarch64-unknown-linux-gnu "
            f"--prefix={self.package_folder} --enable-client-only "
            "--disable-zlib",
            cwd=work,
        )
        # --disable-zlib 未让 config.h 的 HAVE_LIBZ undef（zlib 头/库检测
        # 通过——实测仍 #define HAVE_LIBZ 1）→ binflate.c 的 zlib 代码
        # （#ifdef HAVE_LIBZ 条件编译）被编译 → libbac.so 链接引用非 PIC
        # zlib 的 z_errmsg → R_AARCH64 重定位失败。**强制 undef HAVE_LIBZ**
        # （利用已有条件编译——zlib 代码被排除，libbac 无 zlib 引用）
        cfg_path = os.path.join(work, "src", "config.h")
        cfg = open(cfg_path).read()
        cfg = cfg.replace("#define HAVE_LIBZ 1", "/* #undef HAVE_LIBZ */")
        open(cfg_path, "w").write(cfg)
        print("config.h HAVE_LIBZ forced undef (disable zlib)")
        # src/filed/Makefile: OHOS 未启用 xattr → XATTROBJS 为空（bxattr.o
        # 不在链接对象——stub 版 bxattr.o 编译了也不链接 → filed 链接
        # undefined new_bxattr/BXATTR 符号）——XATTROBJS 补 bxattr.o
        mf = os.path.join(work, "src", "filed", "Makefile")
        ms = open(mf).read()
        ms = ms.replace("XATTROBJS = ", "XATTROBJS = bxattr.o", 1)
        open(mf, "w").write(ms)
        print("filed Makefile XATTROBJS += bxattr.o")
        # build the File Daemon only——依赖链：src/lib（libbac 基础库）
        # → src/findlib（libbacfind）→ src/filed（bacula-fd），逐个先构建
        # （实测 findlib 报 'No rule to make target ../lib/libbac.la'）
        self.run("make -C src/lib", cwd=work)
        self.run("make -C src/findlib", cwd=work)
        self.run("make -C src/filed", cwd=work)

    def package(self):
        work = "/data/storage/el2/base/cache/bacula-fd-src-3"
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        shutil.copy2(os.path.join(work, "src", "filed", ".libs", "bacula-fd"),
                     os.path.join(bin_dir, "bacula-fd"))

    def package_info(self):
        self.conf_info.define("user.bacula-fd:exe", os.path.join(
            self.package_folder, "bin", "bacula-fd"))
