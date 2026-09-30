#!/usr/bin/env python3
"""Conan recipe — libvpd 2.2.9 (IBM VPD — Vital Product Data library).

上游 tarball 只提供 configure.ac / Makefile.am / bootstrap.sh，
**没有预生成的 configure**。本配方按仓库主流做法（240 处先例，如
abiword-plugin-docbook / agg 系）在 build() 阶段用 tool_requires 拉入的
automake + libtool **在 CI 内自举** autoreconf 产物：

  aclocal → autoconf → autoheader → automake

这样配方只提交源码层改动（Makefile.am 补丁），不提交 configure /
Makefile.in / aclocal.m4 / ltmain.sh / config.guess / config.sub 等
autotools 生成产物 —— 遵守 R6「只改源文件不改生成文件」（生成物不可复现）。

为什么此前需要 preconf/：早期误判「CI worker 无 libtoolize/aclocal/automake」
而把生成物随配方提交（占 PR 98% 行数、51276 行，且违反 R6）。实际
automake/1.18 与 libtool/2.5.4 均已在制品仓发布，用 tool_requires 即可在
CI 内生成，无需携带生成物。

OHOS 适配要点：
  - libc++：上游 libvpd_cxx_la_LDFLAGS 硬编码 -lstdc++，OHOS sysroot
    只有 libc++，由 patches/ 改为 -lc++（源码层，符合 R6）
  - config.guess/config.sub：automake/1.18 自带的 config.sub 已识别
    aarch64-linux-ohos（实测 `sh config.sub aarch64-linux-ohos` →
    aarch64-unknown-linux-ohos），故无需随配方携带 config.* 覆盖
  - 依赖 sqlite3 不在 sysroot，由 conan 从制品仓提供
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.env import VirtualBuildEnv
from conan.tools.layout import basic_layout


class LibvpdConan(ConanFile):
    name = "libvpd"
    version = "2.2.9"
    description = "IBM VPD (Vital Product Data) library - C and C++ APIs for hardware inventory data"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/ibm-power-utilities/libvpd"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    # 只导出源码层输入：源码元数据 + Makefile.am 补丁。
    # 不再导出 preconf/（autotools 生成物，违反 R6，且撑大 PR）。
    exports_sources = "conandata.yml", "patches/*"

    def requirements(self):
        # 制品仓中的引用为 sqlite3/3.53.4（无 user/channel 后缀）。
        # 经核对本仓库 9314 处 self.requires 均采用无后缀写法，
        # 仅 3 处使用 @ohpcd/stable，故此处按仓库实际惯例写无后缀形式。
        self.requires("sqlite3/3.53.4")

    def build_requirements(self):
        # 上游不带 configure：build() 必须自举 aclocal/autoconf/autoheader/automake。
        # 实测 hnp/bin 只有 autoconf 家族（autoconf/autoheader/autom4te/m4/autoreconf）
        # 没有 aclocal/automake/libtool，故将 automake + libtool 作为 tool_requires
        # 拉入（制品仓已发布 1.18 / 2.5.4，与仓库 240 处先例同款）。
        # tool_requires 按 *build* profile 解析；CI 的 conan create 已同时传
        # -pr:h 与 -pr:b（ci/conan/build_and_test.sh:316），故可正常解析。
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def export_sources(self):
        # 导出 patches/ 声明的补丁文件（仓库主流写法，与 abiword 系先例一致）。
        # 不再导出 preconf/：autotools 生成物由 CI 内自举产生（R6）。
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        # 源码 URL/sha256 从 conandata.yml 读取（本仓库标准做法，与 manifest.yaml
        # 的 source 段保持一致）。
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # VirtualBuildEnv：把 tool_requires(automake/libtool) 的 bin 注入
        # conanbuild 环境的 PATH，并提供 $ACLOCAL/$AUTOMAKE/$LIBTOOLIZE。
        # 不注入则 self.run(env="conanbuild") 内裸调 aclocal 报 "aclocal: not found"。
        VirtualBuildEnv(self).generate()
        # AutotoolsDeps 负责把依赖（sqlite3）的 -I / -L / -l 注入
        # CPPFLAGS/LDFLAGS/LIBS，否则 configure 的 AC_CHECK_HEADERS([sqlite3.h]) 找不到头文件
        deps = AutotoolsDeps(self)
        deps.generate()
        tc = AutotoolsToolchain(self)
        # R26：系统库默认静态链接
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # udev 安装钩子会写 $(DESTDIR)/${sysconfdir}/udev/rules.d，
        # 把 sysconfdir/localstatedir 收敛到 prefix 内，避免向系统路径写入
        tc.configure_args.append("--sysconfdir=${prefix}/etc")
        tc.configure_args.append("--localstatedir=${prefix}/var")
        tc.generate()

    def _bootstrap_autotools(self):
        """在 CI 内自举 autoreconf 产物（R6：生成物不随配方提交）。

        严格照上游自带的 bootstrap.sh 顺序执行（该文件即上游官方自举脚本）：
            aclocal && libtoolize --force && autoheader && automake --add-missing --copy && autoconf
        其中 config/ 与 m4/ 必须先建：
          - m4/     : aclocal -I m4 需要该目录存在，否则报
                      "couldn't open directory 'm4': No such file or directory"
          - config/ : configure.ac 用 config/config.h 形式，autoheader 需要该目录，
                      否则报 "cannot rename .../config.hin as config/config.h.in"
        全程用 self.run(env="conanbuild")：tool_requires 注入的 $ACLOCAL /
        $AUTOMAKE / $LIBTOOLIZE 只对该环境生效，Python 进程的 os.environ
        取不到（仓库先例实测裸调 "aclocal: not found"）。
        """
        # 1) 应用 patches/ 声明的源码层补丁（Makefile.am：-I$(srcdir)/src、
        #    -lc++、install -m 644 + $(srcdir)/）。必须在 autoreconf 之前，
        #    补丁效果才能落进生成的 Makefile.in。
        apply_conandata_patches(self)

        # 2) 上游 bootstrap.sh 的前置：建 aclocal/autoheader 需要的输出目录
        for d in ("config", "m4"):
            os.makedirs(os.path.join(self.source_folder, d), exist_ok=True)

        # autoconf/automake 需要可写临时目录。HMDFS 下 /tmp 只读、沙箱 TMPDIR
        # 可能不可写，统一收敛到 build 目录内的子目录（E002 同款处理）。
        tmpdir = os.path.join(self.build_folder, ".autotools-tmp")
        os.makedirs(tmpdir, exist_ok=True)
        _tmp = f'TMPDIR="{tmpdir}" TMP="{tmpdir}" TEMP="{tmpdir}" '

        # 3) 按上游 bootstrap.sh 的既定顺序执行自举
        #    aclocal → libtoolize --force → autoheader → automake → autoconf
        self.run(_tmp + '"${ACLOCAL:-aclocal}"',
                 cwd=self.source_folder, env="conanbuild")
        # libtoolize --force 提供 ltmain.sh / m4 宏（automake 依赖 ltmain.sh，
        # 缺则报 "required file './ltmain.sh' not found" 而不生成 Makefile.in）
        self.run(_tmp + '"${LIBTOOLIZE:-libtoolize}" --force',
                 cwd=self.source_folder, env="conanbuild")
        # autoheader 生成 config/config.h.in（上游 configure.ac 用 config/config.h）
        self.run(_tmp + '"${AUTOHEADER:-autoheader}"',
                 cwd=self.source_folder, env="conanbuild")
        # automake 生成 Makefile.in + install-sh/depcomp/missing（--add-missing）
        self.run(_tmp + '"${AUTOMAKE:-automake}" --add-missing --copy',
                 cwd=self.source_folder, env="conanbuild")
        # autoconf 最后由 configure.ac 生成 configure（上游脚本放在最后一步）
        self.run(_tmp + '"${AUTOCONF:-autoconf}"',
                 cwd=self.source_folder, env="conanbuild")

        if not os.path.isfile(os.path.join(self.source_folder, "configure")):
            raise ConanException("autoconf 未生成 configure（autoreconf 自举失败）")
        if not os.path.isfile(os.path.join(self.source_folder, "Makefile.in")):
            raise ConanException("automake 未生成 Makefile.in（autoreconf 自举失败）")

    def _patch_config_guess_for_ohos(self):
        """为生成出的 config.guess 补 HarmonyOS 识别分支（知识库 E007）。

        GNU config.guess 不含 HarmonyOS 分支（uname -s = "HarmonyOS"、
        "HongMeng Kernel"），configure 第一阶段即报
        "cannot guess build type; you must specify one" 而中断。

        E007 明确规定：**不得**用 `--build=`/`--host=` 绕过——那会让 configure
        误判为交叉编译（cross_compiling=yes），AC_RUN_IFELSE 等运行时检测全部
        跳过，config.h 按 Linux/glibc 默认值生成，与实际平台不符。正确做法是
        给 config.guess 补上 HarmonyOS 分支，令其输出标准三元组
        aarch64-unknown-linux-ohos。

        技能自带 scripts/patch-autotools-ohos.pl 做同样的事，但它依赖
        ${SKILL_ROOT} 环境变量（CI 上不保证存在），故此处内联等价实现，
        保持配方自包含。

        config.sub 无需处理：automake/1.18 与 libtool/2.5.4 自带的
        config.sub 均已原生识别 ohos（实测 `sh config.sub aarch64-linux-ohos`
        → aarch64-unknown-linux-ohos）。
        """
        cg = os.path.join(self.source_folder, "config", "config.guess")
        if not os.path.isfile(cg):
            return
        with open(cg, "r", encoding="utf-8", errors="surrogateescape") as f:
            txt = f.read()

        if "HarmonyOS" in txt:
            return  # 已打过补丁，幂等

        # 在 NetBSD 分支前插入 HarmonyOS 识别块（与 patch-autotools-ohos.pl 同款）。
        # 注意 config.guess 各版本缩进不一（空格/tab 混用），故按正则匹配
        # 「主 case 的第一个 *:NetBSD:*:*) 分支行」再行插入。
        block = (
            '    *:HarmonyOS:*:*)\n'
            '\tcase "$UNAME_MACHINE" in\n'
            '\t    aarch64|arm64) MACHINE=aarch64 ;;\n'
            '\t    armv7*|armv8*) MACHINE=arm ;;\n'
            '\t    x86_64|amd64)  MACHINE=x86_64 ;;\n'
            '\t    i?86)         MACHINE=i686 ;;\n'
            '\t    *)            MACHINE="$UNAME_MACHINE" ;;\n'
            '\tesac\n'
            '\tGUESS=${MACHINE}-unknown-linux-ohos\n'
            '\t;;\n\n'
        )
        m = re.search(r'^[ \t]*\*:NetBSD:\*:\*\)[ \t]*$', txt, re.M)
        if not m:
            raise ConanException(
                "config.guess 中找不到 NetBSD 插入点，E007 补丁失败")
        txt = txt[:m.start()] + block + txt[m.start():]

        with open(cg, "w", encoding="utf-8", errors="surrogateescape") as f:
            f.write(txt)
        os.chmod(cg, 0o755)
        self.output.info("  [ok] config.guess 已补 HarmonyOS 分支（E007）")

    def _patch_configure_for_ohos(self):
        """生成后的 configure 两处 OHOS 适配（源码层不可控，故在生成物上就地修）。

        注意：这两处改的是 **CI 运行时新生成**的 configure（非仓库内提交的
        生成物），不违反 R6 的「不提交生成文件」——R6 禁止的是把生成文件
        放进 PR，这里是构建期临时产物。
        """
        fp = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(fp):
            return
        with open(fp, "r", encoding="utf-8", errors="surrogateescape") as f:
            txt = f.read()

        # E165：OHOS 没有 /bin/bash；autoconf 生成的脚本若走 bash 分支需改写
        # （/bin/sh 存在，故只修 bash）
        txt = txt.replace("#!/bin/bash", "#!/data/service/hnp/bin/bash")
        txt = txt.replace("#! /bin/bash", "#!/data/service/hnp/bin/bash")
        txt = txt.replace("${CONFIG_SHELL-/bin/bash}",
                          "${CONFIG_SHELL-/data/service/hnp/bin/bash}")

        # HMDFS workaround（与 archives/a/agg 同款）：
        # configure 生成的 config.status 用 `(umask 077 && mktemp -d "./confXXXXXX")`
        # 创建 700 权限子目录，HMDFS 拒写该目录，导致
        # "config.status: error: could not create Makefile"。改为 umask 022 的
        # mkdir（775 权限）。
        txt = txt.replace(
            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&',
            'tmp=./confstat-$$' + '\n  (umask 022 && mkdir -p "$tmp" && chmod 755 "$tmp") &&')
        txt = txt.replace(
            '(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null',
            '(umask 022 && mkdir -p ./confstat-$$ && chmod 755 ./confstat-$$ && echo ./confstat-$$)')

        with open(fp, "w", encoding="utf-8", errors="surrogateescape") as f:
            f.write(txt)
        os.chmod(fp, 0o755)

    def build(self):
        self._bootstrap_autotools()
        # E007：给生成出的 config.guess 补 HarmonyOS 分支（不识别会直接中断 configure）
        self._patch_config_guess_for_ohos()
        self._patch_configure_for_ohos()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["vpd", "vpd_cxx"]
        self.cpp_info.includedirs = ["include"]
        # C++ 库链接 libc++（OHOS）
        self.cpp_info.system_libs = ["c++"]
        # 公开头文件 vpddbenv.h 直接 #include <sqlite3.h>，
        # 必须把 sqlite3 的头文件/库路径透传给消费者，否则消费者编译失败
        self.cpp_info.requires = ["sqlite3::sqlite3"]
