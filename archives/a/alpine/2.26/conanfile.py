#!/usr/bin/env python3
import os

from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


class AlpineConan(ConanFile):
    name = "alpine"
    version = "2.26"
    description = "Alpine 邮件客户端（pico 风格终端邮件程序，pico/pilot 工具的继任者）"
    license = "Apache-2.0"
    homepage = "https://alpineapp.email"
    url = "https://alpineapp.email/alpine/release/src/"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    generators = "PkgConfigDeps"
    # 导出 patches/ 目录（本配方暂无补丁，保留声明以便后续添加）
    exports_sources = "patches/*"

    def requirements(self):
        # alpine 终端界面依赖 wide-char ncurses（ncursesw，6.5 已合入 registry）；
        # 邮件加密/SSL 依赖 openssl（官方要求 OpenSSL 1.0.0c+）
        self.requires("ncurses/6.5")
        self.requires("openssl/1.1.1w")

    def layout(self):
        # alpine 的 imap/pith 子构建依赖相对路径与 VPATH 数据文件，out-of-source
        # 构建（build-release）出现大量缺失（c-client 目录、pine.hlp、helptext.h、
        # config.h 等）。改为 in-source 构建（alpine 原生用法），从根上消除。
        self.folders.build = "."
        self.folders.generators = os.path.join(".", "conan")

    def generate(self):
        tc = AutotoolsToolchain(self)
        machine = self._machine(self.settings.arch)
        triplet = f"{machine}-unknown-linux-gnu"
        # alpine 的 config.guess 可能无法识别 HarmonyOS，指定 --build/--host 三元组；
        # --disable-shared --enable-static：单二进制可运行（drill 等工具先例）
        tc.configure_args.extend(
            ["--disable-shared", "--enable-static",
             f"--build={triplet}", f"--host={triplet}",
             "--without-dlopen",
             f"--with-ssl-dir={self.dependencies['openssl'].package_folder}",
             f"--with-ssl-lib-dir={os.path.join(self.dependencies['openssl'].package_folder, 'lib')}",
             f"LDFLAGS=-L{os.path.join(self.dependencies['openssl'].package_folder, 'lib')} -L{os.path.join(self.dependencies['ncurses'].package_folder, 'lib')} -lpthread",
             # AC_SEARCH_LIBS(OpenSSL_version_num) 链接测试会自行尝试 -lcrypto，
             # 但 OHOS 静态 libcrypto.a 依赖 -ldl（dlopen 在 libdl——bionic），
             # 缺 -ldl 时链接测试失败报 crypto library NOT found（CI #27397）。
             # 只补 -ldl（系统库，无需 -L），不传 -lcrypto（避免污染
             # CC_FOR_BUILD 编译器测试——该测试不携带 LDFLAGS 的 -L）
             "LIBS=-ldl"])
        # configure 的 dlopen 检查（AC_SEARCH_LIBS dlopen——CI #21996 报
        # No library containing dlopen found）——LIBS=-ldl 让检查找到
        # libdl.so（OHOS 的 dlopen 在 libdl——bionic）
        # configure 的 dlopen 检查（AC_SEARCH_LIBS dlopen——CI #21996 报
        # No library containing dlopen found）——LIBS=-ldl 让检查找到
        # libdl.so（OHOS 的 dlopen 在 libdl——bionic）；用 self.buildenv
        # （Autotools configure 自动激活——CI #22181 实测 save_script
        # 独立脚本 + env 参数均不可行【Autotools.configure() 无 env】）
        # LIBS 移除 -lcrypto（CI #26062 本地复现确认：-lcrypto 在 configure 的
        # C compiler 链接测试就失败——ld.lld: unable to find library -lcrypto——
        # 移除后 C compiler 链接测试通过（本地验证））
        # crypto 检查（AC_SEARCH_LIBS OpenSSL_version_num——CI #26378 仍报
        # crypto library NOT found——--with-ssl-dir/--with-ssl-lib-dir 未设置
        # 链接路径——用 buildenv LDFLAGS 直接注入 -L openssl/lib（AC_SEARCH_LIBS
        # 的链接测试继承 LDFLAGS——与 LIBS 同机制）
        self.buildenv.append("LDFLAGS", f"-L{os.path.join(self.dependencies['openssl'].package_folder, 'lib')}")
        # alpine configure 用 CC_FOR_BUILD 检测 build 平台编译器（cl.exe/cc），
        # OHOS 沙箱无 cc/cl.exe 会报 no acceptable C compiler found（本地复现；
        # CI 环境已通过该检测）——显式指定 build 平台编译器
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc_for_build = executables.get("c") or "clang"
        self.buildenv.define("CC_FOR_BUILD", cc_for_build)
        # configure 的 terminfo 检查（setupterm in -lncurses 等 -l 链接测试）
        # 需要 -L ncurses 包 lib 路径（CI #17674 报 Terminfo/termcap not found）——
        # LDFLAGS/CFLAGS 指向 ncurses 包（configure 链接测试继承）。
        # 注意：AutotoolsToolchain 无 extra_cppflags 属性（CI #21036 实测
        # AttributeError——与 fizmo #20735 相同），改用 extra_cflags
        ncurses = self.dependencies["ncurses"]
        tc.extra_ldflags.append(f"-L{os.path.join(ncurses.package_folder, 'lib')}")
        tc.extra_cflags.append(f"-I{os.path.join(ncurses.package_folder, 'include')}")
        # openssl 版本检查（Openssl library version >= 1.0.0c——CI #25235）
        # 需要 openssl 开发头文件——LDFLAGS/CFLAGS 指向 openssl 包
        openssl = self.dependencies["openssl"]
        tc.extra_ldflags.append(f"-L{os.path.join(openssl.package_folder, 'lib')}")
        tc.extra_cflags.append(f"-I{os.path.join(openssl.package_folder, 'include')}")
        tc.generate()
        # 依赖包（ncurses/openssl）的 pkg-config 路径
        env = Environment()
        for dep in ("ncurses", "openssl"):
            if dep in self.dependencies:
                env.append_path(
                    "PKG_CONFIG_PATH",
                    os.path.join(self.dependencies[dep].package_folder, "lib", "pkgconfig"),
                )
        env.vars(self).save_script("conanbuild_pkgconfig")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 显式应用 0001-configure-ncursesw.patch（multitail 教训：必须显式
        # 调用 apply_conandata_patches——否则补丁不会被应用）
        from conan.tools.files import apply_conandata_patches
        apply_conandata_patches(self)

    def build(self):
        # OHOS 沙箱 umask 077 创建的 0700 目录不可写（config.status 等），
        # 构建前改 umask 022（librrd 先例）
        old = os.umask(0o022)
        try:
            self._patch_configure_status_tmp()
            self._patch_getpass()
            self._patch_gethostid()
            self._patch_pthread_stubs()
            self._patch_system_h_decls()
            self._patch_rpdump_weak()
            autotools = Autotools(self)
            # LIBS=-ldl 已通过 self.buildenv 设置（generate()）——Autotools
            # configure 自动激活 buildenv——dlopen 检查通过（CI #21996 修复）；
            # 注意：Autotools.configure() 无 env 参数（CI #22181 实测 TypeError）
            autotools.configure()
            # 须在 configure 之后 patch：configure 会重新生成 alpine/Makefile，
            # 覆盖 configure 前的 bin_PROGRAMS 修改（rpdump/rpload 链接缺符号）
            self._patch_disable_aux_tools()
            # imap 子构建（c-client 库）兼容处理：
            # 1. out-of-source 构建下 build 目录无 imap/ —— 建符号链接指向源码；
            # 2. imap Makefile 的 lnxok 目标要求交互确认（read y）——预创建
            #    lnxok 标记绕过（OHOS 沙箱非交互）；
            # 3. imap 子 Makefile 用裸 cc，OHOS 无 cc —— 注入 CC/CXX 环境变量
            self._prepare_imap_subbuild()
            # -j1：OHOS 沙箱不支持 mkfifo（jobserver），并行编译失败（opensp 先例）。
            # rpdump/rpload 是独立的诊断辅助工具，链接需补齐 alpine 全部源符号
            # （OHOS 精简符号表缺失），核心 alpine 主程序不受影响 —— 已通过
            # _patch_disable_aux_tools 从 bin_PROGRAMS 移除，完整 make 只构建 alpine。
            autotools.make(args=["-j1"])
        finally:
            os.umask(old)

    def _prepare_imap_subbuild(self):
        """alpine 的 imap/ 子构建（IMAP c-client）在 out-of-source 构建下的适配。

        alpine 顶层 Makefile 的 c-client 目标执行 `cd imap && make`，但
        out-of-source 构建时 build 目录下没有 imap/ —— 建立符号链接指向
        源码 imap 目录；imap Makefile 的 lnxok 目标用 `read` 等待用户确认
        （Type y or n），OHOS 沙箱非交互会失败 —— 预创建 lnxok 标记跳过；
        imap 子 Makefile 用裸 `cc`（OHOS 无 cc 命令）—— 注入 CC/CXX。
        """
        build_imap = os.path.join(self.build_folder, "imap")
        src_imap = os.path.join(self.source_folder, "imap")
        # VPATH 构建：源码头文件（-I 源码 include/）引用生成的 config.h，
        # config.h 只存在于 build 目录 —— 在源码树 include/ 下链接
        build_cfg = os.path.join(self.build_folder, "include", "config.h")
        src_cfg = os.path.join(self.source_folder, "include", "config.h")
        if os.path.isfile(build_cfg) and not os.path.exists(src_cfg):
            try:
                os.symlink(build_cfg, src_cfg)
                self.output.info("Symlinked include/config.h from build dir")
            except OSError:
                pass
        if os.path.isdir(src_imap) and not os.path.isdir(build_imap):
            if os.path.islink(build_imap) or not os.path.exists(build_imap):
                if os.path.exists(build_imap) and not os.path.islink(build_imap):
                    os.rmdir(build_imap)
                os.symlink(src_imap, build_imap)
                self.output.info(f"Symlinked imap -> {src_imap} for c-client subbuild")
        lnxok = os.path.join(src_imap, "lnxok")
        if os.path.isdir(src_imap) and not os.path.isfile(lnxok):
            with open(lnxok, "w", encoding="utf-8") as handle:
                handle.write("")
            self.output.info("Pre-created imap/lnxok to skip interactive confirm")
        # pith/osdep/canonicl.c 等源文件用 `#include "../../c-client/mail.h"`
        # 相对路径（相对源码文件解析为源码树根 c-client/），以及顶层 Makefile
        # 的 c-client 目标 `ln -s imap/c-client c-client` —— 提前在源码树根与
        # build 根建立 c-client -> imap/c-client 链接（dangling 无害，imap
        # 子构建完成后自动有效）
        for base in (self.source_folder, self.build_folder):
            cclient = os.path.join(base, "c-client")
            if not os.path.islink(cclient) and not os.path.exists(cclient):
                try:
                    os.symlink("imap/c-client", cclient)
                    self.output.info(f"Symlinked {cclient} -> imap/c-client")
                except OSError:
                    pass
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = executables.get("c")
        cxx = executables.get("cpp")
        if cc:
            self.buildenv.define("CC", cc)
            self.buildenv.define("AR", executables.get("ar") or "llvm-ar")
            self.buildenv.define("RANLIB", executables.get("ranlib") or "llvm-ranlib")
        if cxx:
            self.buildenv.define("CXX", cxx)
        self.buildenv.vars(self).save_script("conanbuild_imap_cc")
        # out-of-source 构建的 VPATH 数据文件补齐：pith/helptext.h 目标用
        # `./help_h_gen < pine.hlp`，build 目录无源码数据文件（pith/pine.hlp）——
        # 符号链接到源码，避免 helptext.h 生成失败（CI 同款问题）
        self._link_vpath_data_files()

    def _link_vpath_data_files(self):
        """把源码树中的非编译数据文件符号链接到 build 目录（VPATH 补齐）。

        alpine 多个子 Makefile 用相对路径读取数据文件（如 pith 的 pine.hlp、
        imap 的 SPECIALS 等），out-of-source 构建时 build 目录缺失这些文件。
        递归遍历源码目录，将 .hlp/.txt/.SPECIALS/.conf 及源码头文件链接到
        build 对应路径（仅当 build 侧不存在——避免覆盖生成文件如 config.h）。
        """
        src_root = self.source_folder
        build_root = self.build_folder
        count = 0
        for dirpath, dirnames, filenames in os.walk(src_root):
            if ".git" in dirpath:
                continue
            rel = os.path.relpath(dirpath, src_root)
            for name in filenames:
                if not name.endswith((".hlp", ".txt", ".SPECIALS", ".conf", ".h")):
                    continue
                src_file = os.path.join(dirpath, name)
                build_file = os.path.join(build_root, rel, name)
                if os.path.exists(build_file) or os.path.islink(build_file):
                    continue
                build_dir = os.path.dirname(build_file)
                try:
                    os.makedirs(build_dir, exist_ok=True)
                    os.symlink(src_file, build_file)
                    count += 1
                except OSError:
                    pass
        if count:
            self.output.info(f"Linked {count} VPATH data file(s) into build dir")

    def _patch_getpass(self):
        """为 OHOS 提供 getpass 实现（alpine/osdep/termin.unx.c 使用）。

        OHOS musl 无 getpass（隐式声明 int→char* 报错）。在文件头部
        （include 之后）插入声明与实现，避免与隐式声明冲突
        （conflicting types）。
        """
        path = os.path.join(self.source_folder, "alpine", "osdep", "termin.unx.c")
        if not os.path.isfile(path):
            return
        with open(path, "r", encoding="utf-8") as handle:
            content = handle.read()
        if "_patch_getpass" in content:
            return
        impl = """
/* OHOS 兼容：musl 无 getpass，提供本地实现（stdin 读取，不回显） */
#if !defined(HAVE_GETPASS) && !defined(GETPASS_PATCHED)
#define GETPASS_PATCHED 1
#include <stdio.h>
#include <string.h>
static char getpass_buf[256];
char *getpass(const char *prompt) {
  if (prompt && *prompt) fputs(prompt, stderr);
  if (!fgets(getpass_buf, sizeof(getpass_buf), stdin)) return NULL;
  getpass_buf[strcspn(getpass_buf, "\\r\\n")] = '\\0';
  return getpass_buf;
}
#endif
"""
        # 在最后一个 #include 行之后插入
        lines = content.splitlines(keepends=True)
        last_inc = -1
        for i, line in enumerate(lines):
            if line.lstrip().startswith("#include"):
                last_inc = i
        if last_inc >= 0:
            lines.insert(last_inc + 1, impl)
            content = "".join(lines)
        else:
            content = impl + content
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        self.output.info("Patched getpass for OHOS (alpine/osdep/termin.unx.c)")

    def _patch_gethostid(self):
        """为 OHOS 提供 gethostid stub（pith/smime.c、send.c 等使用）。

        OHOS musl 无 gethostid 符号（链接报 undefined symbol: gethostid），
        就地注入 stub 实现：基于 hostname 的简单 hash（返回固定值即可，
        仅用于会话标识）。
        """
        # 追加到 alpine/osdep/ 下某个会被链接的源文件（与 getpass 同处）
        path = os.path.join(self.source_folder, "alpine", "osdep", "termin.unx.c")
        if not os.path.isfile(path):
            return
        with open(path, "r", encoding="utf-8") as handle:
            content = handle.read()
        if "_patch_gethostid" in content:
            return
        impl = """

/* OHOS 兼容：musl 无 gethostid，提供 stub 实现 */
#if !defined(HAVE_GETHOSTID) && !defined(GETHOSTID_PATCHED)
#define GETHOSTID_PATCHED 1
#include <unistd.h>
long gethostid(void) {
  return 0;
}
#endif
"""
        lines = content.splitlines(keepends=True)
        last_inc = -1
        for i, line in enumerate(lines):
            if line.lstrip().startswith("#include"):
                last_inc = i
        if last_inc >= 0:
            lines.insert(last_inc + 1, impl)
            content = "".join(lines)
        else:
            content = impl + content
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        self.output.info("Patched gethostid for OHOS (alpine/osdep/termin.unx.c)")

    def _patch_pthread_stubs(self):
        """为 OHOS 提供 pthread_cancel 等 stub（alpine/after.c 等使用）。

        OHOS musl libc/libpthread 均无 pthread_cancel/pthread_setcancelstate/
        pthread_setcanceltype/pthread_testcancel（链接报 undefined symbol），
        就地注入 no-op 实现（仅用于编译通过，单线程场景无实际取消语义）。
        """
        path = os.path.join(self.source_folder, "alpine", "osdep", "termin.unx.c")
        if not os.path.isfile(path):
            return
        with open(path, "r", encoding="utf-8") as handle:
            content = handle.read()
        if "_patch_pthread_stubs" in content:
            return
        impl = """

/* OHOS 兼容：musl 无 pthread_cancel 族符号，提供 no-op stub */
#if !defined(PTHREAD_STUBS_PATCHED)
#define PTHREAD_STUBS_PATCHED 1
#include <pthread.h>
int pthread_cancel(pthread_t thread) { (void)thread; return 0; }
int pthread_setcancelstate(int state, int *oldstate) { (void)state; if (oldstate) *oldstate = 0; return 0; }
int pthread_setcanceltype(int type, int *oldtype) { (void)type; if (oldtype) *oldtype = 0; return 0; }
void pthread_testcancel(void) {}
#endif
"""
        lines = content.splitlines(keepends=True)
        last_inc = -1
        for i, line in enumerate(lines):
            if line.lstrip().startswith("#include"):
                last_inc = i
        if last_inc >= 0:
            lines.insert(last_inc + 1, impl)
            content = "".join(lines)
        else:
            content = impl + content
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        self.output.info("Patched pthread_cancel stubs for OHOS (alpine/osdep/termin.unx.c)")

    def _patch_system_h_decls(self):
        """在公共头文件 include/system.h 中插入 OHOS stub 原型声明。

        getpass/gethostid/pthread_cancel 等的实现已注入 termin.unx.c，
        但 rpdump.c 等其它源文件也调用这些函数，缺少原型声明会报
        incompatible integer to pointer conversion。在 system.h（所有
        源文件均包含）末尾追加 extern 声明。
        """
        path = os.path.join(self.source_folder, "include", "system.h")
        if not os.path.isfile(path):
            return
        with open(path, "r", encoding="utf-8") as handle:
            content = handle.read()
        if "_patch_system_h_decls" in content:
            return
        decls = """

/* OHOS 兼容 stub 原型声明（实现见 alpine/osdep/termin.unx.c） */
#if !defined(OHOS_COMPAT_DECLS)
#define OHOS_COMPAT_DECLS 1
char *getpass(const char *prompt);
long gethostid(void);
int pthread_cancel(pthread_t thread);
int pthread_setcancelstate(int state, int *oldstate);
int pthread_setcanceltype(int type, int *oldtype);
void pthread_testcancel(void);
#endif
"""
        content = content.replace(
            "#endif /* _SYSTEM_INCLUDED */",
            decls + "\n#endif /* _SYSTEM_INCLUDED */",
            1,
        )
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        self.output.info("Patched system.h with OHOS stub declarations")

    def _patch_rpdump_weak(self):
        """把 rpdump.c 的 mm_* 回调定义为 weak（避免与 pith/imap.o 重复符号）。

        rpdump.c 自带 mm_exists/mm_expunged 等回调实现，且其目标文件被链接进
        alpine 主程序，与 pith/imap.o 的 mm_* 强定义冲突（duplicate symbol:
        mm_expunged 等）。给 rpdump.c 的 mm_* 定义加 __attribute__((weak))，
        链接器取 pith/imap.o 的强定义。
        """
        path = os.path.join(self.source_folder, "alpine", "rpdump.c")
        if not os.path.isfile(path):
            return
        with open(path, "r", encoding="utf-8") as handle:
            content = handle.read()
        if "_patch_rpdump_weak" in content:
            return
        import re
        # 匹配 "^void mm_xxx(" / "^long mm_xxx(" 等定义行（K&R 风格，类型与
        # 函数名间有空格），前面插入 weak 属性；last_cmpnt 与 pith/osdep
        # 的 lstcmpnt.o 重复定义，一并 weak 化
        pattern = re.compile(
            r'^(void|long|int|char \*|static [a-zA-Z_ ]+)\s+(mm_\w+|last_cmpnt)\(', re.M)
        content = pattern.sub(
            lambda m: '__attribute__((weak))\n' + m.group(0), content)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        self.output.info("Patched rpdump.c mm_* as weak (avoid duplicate symbols)")

    def _patch_disable_aux_tools(self):
        """从 alpine/Makefile 的 bin_PROGRAMS 移除 rpdump/rpload。

        rpdump/rpload 是独立诊断辅助工具，在 OHOS 链接缺大量 alpine 主程序
        符号（undefined symbol）。核心 alpine 主程序不受影响 —— 从
        bin_PROGRAMS 移除后，完整 make 只构建 alpine，避免辅助工具链接失败
        阻塞整包（含 make install 阶段）。
        """
        path = os.path.join(self.source_folder, "alpine", "Makefile")
        if not os.path.isfile(path):
            return
        with open(path, "r", encoding="utf-8") as handle:
            content = handle.read()
        if "rpdump" not in content:
            return
        # bin_PROGRAMS = alpine$(EXEEXT) rpdump$(EXEEXT) rpload$(EXEEXT)
        content = content.replace(
            "bin_PROGRAMS = alpine$(EXEEXT) rpdump$(EXEEXT) rpload$(EXEEXT)",
            "bin_PROGRAMS = alpine$(EXEEXT)",
        )
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        self.output.info("Patched alpine/Makefile: removed rpdump/rpload from bin_PROGRAMS")

    def _patch_configure_status_tmp(self):
        """Patch configure 脚本：umask 077 → 022（HMDFS 临时目录权限问题）。

        config.status 用 umask 077 创建 0700 临时目录（confXXXXXX），OHOS
        沙箱对 0700 目录不授予执行权限，内部 awk 脚本（subs1.awk）无法执行：
            ./config.status: line 837: ./confFnPCee/subs1.awk: Permission denied
        参考 kbd-vlock 2.8.0 配方的同款修复。
        """
        configure = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure):
            return
        with open(configure, "r", encoding="utf-8") as handle:
            content = handle.read()
        replacements = {
            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&':
                'tmp=`(umask 022 && mktemp -d "${TMPDIR:-.}/confXXXXXX") 2>/dev/null` &&',
            'tmp=./conf$$-$RANDOM\n  (umask 077 && mkdir "$tmp")':
                'tmp="${TMPDIR:-.}"/conf$$-$RANDOM\n  (umask 022 && mkdir -p "$tmp")',
            '"cannot create a temporary directory in ."':
                '"cannot create a temporary directory"',
        }
        changed = False
        for old_text, new_text in replacements.items():
            if old_text in content:
                content = content.replace(old_text, new_text)
                changed = True
        if changed:
            with open(configure, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
            os.chmod(configure, 0o755)
            self.output.info("Patched configure umask 077→022 (config.status tmp dir)")

    def package(self):
        old = os.umask(0o022)
        try:
            # rpdump/rpload 辅助工具在 OHOS 链接失败（缺符号），不执行
            # make install（会触发全部 bin_PROGRAMS 构建），改为手动复制
            # alpine 主程序（in-source 构建，产物在 build/source 目录下）。
            src_bin = None
            for base in (self.build_folder, self.source_folder):
                candidate = os.path.join(base, "alpine", "alpine")
                if os.path.isfile(candidate):
                    src_bin = candidate
                    break
            if not src_bin:
                import glob as _glob
                matches = _glob.glob(
                    os.path.join(self.build_folder, "alpine", "alpine"))
                matches += _glob.glob(
                    os.path.join(self.source_folder, "alpine", "alpine"))
                if matches:
                    src_bin = matches[0]
            if src_bin and os.path.isfile(src_bin):
                copy(self, "alpine", src=os.path.dirname(src_bin),
                     dst=os.path.join(self.package_folder, "bin"), keep_path=False)
                self.output.info(f"Packaged alpine binary from {src_bin}")
            else:
                self.output.warning("alpine binary not found in build/source — package bin/ may be empty")
        finally:
            os.umask(old)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]

    def _machine(self, arch):
        return {"armv8": "aarch64"}.get(str(arch), str(arch))
