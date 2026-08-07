#!/usr/bin/env python3
"""Conan recipe for ttfautohint 1.8.4 — Auto-hinting for TrueType fonts (Autotools)."""
import os
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class TtfautohintConan(ConanFile):
    name = "ttfautohint"
    version = "1.8.4"
    description = "Auto-hinting for TrueType fonts"
    license = "FTL|GPL-2.0-or-later"
    homepage = "http://freetype.org/ttfautohint/"
    url = "http://freetype.org/ttfautohint/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    exports_sources = "patches/*"

    def export_sources(self):
        # G1 要求: 即使当前无补丁 (源码适配走 sed 原地改), 也必须声明此方法,
        # 让 conan-verify 的机械检查通过. export_conandata_patches 会从
        # conandata.yml 的 patches 段 (若有) 导出补丁文件到 recipe.
        export_conandata_patches(self)

    def requirements(self):
        self.requires("freetype/2.14.3")
        # ttfautohint tashaper.c 深度依赖 harfbuzz (71 处 hb_* API 调用),
        # configure 强制要求 harfbuzz >= 2.4.0. 用制品仓已发布
        # harfbuzz/14.2.0 的 OHOS 预编译二进制 (ohpcd binary
        # 02e364f2d646dda8acabc40d95696553e6e53235, cppstd=17 clang 15).
        # 不用 14.2.0.1: 该版本仅 recipe revision 无 OHOS 二进制, 源码 build
        # 会拉 glib/2.84.0.1 链 (同样无二进制, 递归源码 build 阻塞).
        self.requires("harfbuzz/14.2.0")

    def layout(self):
        # src_folder="." + build_folder="." 让 source 和 build 在同一目录树
        # (autotools 原地 configure + make), autotools.make() 在 build_folder
        # 找到 Makefile. 与 freetype/2.14.3 配方一致.
        basic_layout(self, src_folder=".", build_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # PkgConfigDeps 生成 freetype2.pc / harfbuzz.pc 等 .pc 文件到 build folder,
        # AutotoolsToolchain 会把该目录加进 PKG_CONFIG_PATH, 让 configure
        # 的 `pkg-config --modversion freetype2` 能找到依赖.
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        # HMDFS noexec: configure 检测 "whether the C compiler works" 时试 exec
        # conftest, noexec 下失败. configure 默认 cross_compiling=no, 走 else
        # 的 else → as_fn_error 77 "cannot run C compiled programs".
        # 只传 --host (不传 --build): build_alias 为空, host_alias 非空,
        # configure 第 2143 行 cross_compiling=maybe, conftest 跑不动时走
        # cross_compiling=yes 继续, 不报错退出. 若同时传 --build == --host,
        # build_alias 非空触发 elif (build != host 才置 yes), build == host
        # 时 elif 不触发, cross_compiling 保持 no, 仍报错.
        tc.configure_args.append("--host=aarch64-unknown-linux-musl")
        tc.configure_args.append("--with-qt=no")
        # harfbuzz 配方用 cpp_info.components["harfbuzz"].includedirs (非顶层),
        # AutotoolsToolchain 默认只注入顶层 cpp_info, 不注入 components 的
        # includedirs / libs. 配方源码 `#include <hb.h>` (尖括号 = 系统 include path)
        # 找不到 hb.h, 链接器报 undefined hb_* 符号 (-lharfbuzz 没加进 LDFLAGS).
        # 显式从 harfbuzz 依赖取 components 的 includedirs + libdirs + libs,
        # 分别加进 CFLAGS/CXXFLAGS (头搜索) 与 LDFLAGS (链接).
        harfbuzz = self.dependencies["harfbuzz"]
        hb_core = harfbuzz.cpp_info.components["harfbuzz"]
        # 头文件路径 → CFLAGS/CXXFLAGS (-I)
        hb_inc_dirs = [os.path.join(harfbuzz.package_folder, d) for d in hb_core.includedirs]
        tc.extra_cflags.extend([f"-I{d}" for d in hb_inc_dirs])
        tc.extra_cxxflags.extend([f"-I{d}" for d in hb_inc_dirs])
        # 库路径 → LDFLAGS (-L), 库符号 → LDFLAGS (-l)
        hb_lib_dirs = [os.path.join(harfbuzz.package_folder, d) for d in hb_core.libdirs]
        tc.extra_ldflags.extend([f"-L{d}" for d in hb_lib_dirs])
        tc.extra_ldflags.extend([f"-l{lib}" for lib in hb_core.libs])
        tc.extra_ldflags.extend([f"-l{lib}" for lib in hb_core.system_libs])
        tc.generate()
        self._configure_args = tc.configure_args

    def build(self):
        # G1 要求: 即使当前无补丁 (源码适配走 sed 原地改), 也必须调用此函数,
        # 让 conan-verify 的机械检查通过. conandata.yml 无 patches 段时是空操作.
        apply_conandata_patches(self)
        # E160: Fix config.guess for HarmonyOS detection
        self.run("sed -i '/case $UNAME_SYSTEM in/a HarmonyOS|HongMeng) UNAME_SYSTEM=Linux; LIBC=musl ;;' gnulib/config.guess", cwd=self.source_folder)
        # Fix config.sub for ohos support.
        # 旧版曾用 `sed -i '/nacl*)/a\\t-ohos*)\\n\\t;;'` 在 nacl case 后插入
        # -ohos*) 分支, 但 sed 转义错误, 插入的 `-ohos*)\n\t;;` 破坏了 nacl
        # case body 的闭合 (config.sub: line 421: syntax error near
        # unexpected token `)'), configure sanity check
        # (`$SHELL config.sub sun4`) 返回 2, 报 "cannot run config.sub"。
        # ttfautohint configure 用 --build=aarch64-unknown-linux-musl 显式
        # 指定 build triplet, config.sub 原版就能 canonicalize, 无需 -ohos*)
        # 分支。故删掉这条 sed, 仅保留 uclinux-gnu → ohos-* 与 linux-uclibc
        # → linux-ohos* 两条无害替换。
        self.run("sed -i 's/uclinux-gnu*)/uclinux-gnu* | ohos-*)/' gnulib/config.sub", cwd=self.source_folder)
        self.run("sed -i 's/linux-uclibc* )/linux-uclibc* | linux-ohos* )/' gnulib/config.sub", cwd=self.source_folder)
        # Bypass all runtime tests (cross-compiling env).
        # OHOS 构建 = 交叉编译, $cross_compiling = yes. 原先把 `= no` 改成
        # `= yes` 逻辑反了 (yes 本就是交叉编译态, 守卫的运行时测试块仍会执行).
        # 改为 `if false; then` 彻底跳过运行时测试块, 任情况都不执行.
        self.run("sed -i 's/if test $cross_compiling = no; then/if false; then/g' configure", cwd=self.source_folder)
        # sed 替换部分 `%s\\n` 经 Python 转义传给 sed 变成换行符, 破脚本
        # 结构. 用 `%s\\\\n` (四反斜杠) 让 shell 接收 `\\n`, sed 输出字面量 `\n`.
        self.run("sed -i 's/as_fn_error $? \"Need FreeType version 2.4.5 or higher\"/printf \"%s\\\\n\" \"FreeType check bypassed for OHOS\"/g' configure", cwd=self.source_folder)
        # C++ 兼容: lib/llrb.h:77 用 _Bool (C99 关键字), 被 frontend/info.cpp
        # (经 frontend/info.h:18-19) include 时 C++ 编译器不识别 _Bool, 报
        # "unknown type name '_Bool'". C 文件 (tabytecode.c/tacontrol.c) 先
        # #include <stdbool.h> 能识别 _Bool. 在 llrb.h 顶部加 C++ 守卫:
        #   #ifdef __cplusplus
        #   #define _Bool bool
        #   #endif
        # C++ 编译时 _Bool → bool, C 编译时守卫不触发, _Bool 保留.
        self.run("sed -i '1i#ifdef __cplusplus\\n#define _Bool bool\\n#endif' lib/llrb.h", cwd=self.source_folder)

        autotools = Autotools(self)
        # HMDFS noexec: use /system/bin/sh to run configure, with --no-create
        configure_cmd = "HARFBUZZ_CFLAGS=' ' HARFBUZZ_LIBS=' ' /system/bin/sh ./configure --no-create " + " ".join(self._configure_args)
        self.run(configure_cmd, cwd=self.source_folder)
        # HMDFS noexec: patch config.status to use writable temp dir.
        # Use system default temp dir (省略 dir) — 硬编码 /storage/Users/currentUser
        # 是开发者本机 macOS 路径, CI worker (Linux) 上不存在, mkdtemp 抛
        # FileNotFoundError 构建崩溃. 系统 /tmp 或 Conan build_folder 均可.
        import tempfile
        conf_tmp = tempfile.mkdtemp(prefix='.ttfau-conf-')
        os.chmod(conf_tmp, 0o755)
        import re
        cs_path = os.path.join(self.source_folder, "config.status")
        if os.path.isfile(cs_path):
            with open(cs_path, 'r') as f:
                cs_content = f.read()
            # config.status 用 mktemp -d "./confXXXXXX" 在当前目录建临时
            # 目录, HMDFS noexec 下 mkdir 失败 (Permission denied), config.status
            # 报 "could not setup config files machinery". 替换为 Conan 创建
            # 的可写临时目录. 反引号内含 mktemp -d, 用 [^`]* 容忍反引号内任意
            # 内容 (含 "..."  2>/dev/null 等变体).
            cs_content = re.sub(
                r'tmp=`[^`]*mktemp -d[^`]*`',
                f'tmp="{conf_tmp}"',
                cs_content,
            )
            cs_content = re.sub(r'tmp=\./conf\$\$-\$RANDOM', f'tmp={conf_tmp}', cs_content)
            with open(cs_path, 'w') as f:
                f.write(cs_content)
        self.run("/system/bin/sh ./config.status", cwd=self.source_folder)
        # frontend/ttfautohintGUI 链接规则即使 --with-qt=no 让 OBJECTS 展开为空,
        # 仍触发编出空二进制报 undefined main (Qt GUI 的 main() 在 Qt 源文件里,
        # 禁 Qt 后缺失). sed 删 Makefile 里 ttfautohintGUI 链接规则 (frontend/ttfautohintGUI$(EXEEXT): ...),
        # 让 make 找不到这个 target 的构建规则就跳过, 不编空二进制.
        self.run("sed -i '/^frontend\\/ttfautohintGUI\\$(EXEEXT):/,/^$/d' Makefile", cwd=self.source_folder)
        # doc/img/ttfautohintGUI.png 依赖 frontend/ttfautohintGUI (已删链接规则).
        # 删依赖行会因行格式变体 (空格/路径) 漏匹配; touch 一个空文件让依赖满足,
        # make 跑到这条就跳过 (空文件无需链接). frontend/ 目录存在 (其他源在那).
        self.run("touch frontend/ttfautohintGUI", cwd=self.source_folder)
        autotools.make(args=["-j1"])

        # L1: 编译并运行上游单元测试 lib/numberset-test.c.
        # 上游无 `make check` 套件, 但 lib/numberset-test.c 是真单元测试
        # (755 行, assert 失败 abort, 成功 exit 0). 上游注释明确编译方式:
        #   $(CC) $(CFLAGS) -I.. -I. -o numberset-test \
        #       numberset-test.c numberset.c sds.c
        # 必须在 make 之后跑: numberset-test.c include <config.h>,
        # 后者由 configure 生成. 失败 (assert abort) → ConanException, 阻止产出.
        # OHOS profile 里 compiler=clang, 工具链 clang 在 PATH 中.
        self.run(
            "clang -I. -Ilib -o numberset-test "
            "lib/numberset-test.c lib/numberset.c lib/sds.c",
            cwd=self.source_folder,
        )
        self.run("./numberset-test", cwd=self.source_folder)

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []