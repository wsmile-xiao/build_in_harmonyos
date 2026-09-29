#!/usr/bin/env python3
"""Conan recipe — mfterm 1.0.7（autotools / C99 CLI，libnfc Mifare Classic 终端）.

mfterm 是基于 libnfc + readline 的 Mifare Classic 标签终端工具，产物为
单个 bin/mfterm 可执行文件（application 型，同 m1ddc / libnfc-tools 口径）。

构建系统：autotools。GitHub tag 归档不含生成的 configure，须按上游
autogen.sh 自举（AUTOMAKE="automake --foreign" autoreconf -fi）。

上游依赖（configure.ac）：libnfc>=1.7（nfc_open）、readline
（rl_completion_matches）、libcrypto（DES_set_key_unchecked —— OpenSSL 3.x
低层 API，已弃用但仍保留，OpenSSL 4.x 将移除，故锁 openssl/3.5.6）。

鸿蒙适配要点：
  - E074: HMDFS 并行 make 触发 jobserver fifo EPERM → make -j1
  - E114: 生成的 configure 中 umask 077 + mktemp 在 HMDFS 产生不可写
    setgid 目录 → 剥离 umask 077（同 abiword-plugin-* 先例）
  - OHOS clang 包装器在 -c 阶段注入 -Wl,--code-sign 触发
    -Werror=unused-command-line-argument → 精准放行该单一告警
  - bison/3.8.2 conan 包 --prefix= 导致内置 pkgdatadir 失效 → 运行时
    重定向 BISON_PKGDATADIR；bison 在 OHOS 上 spawn m4 传空 argv[0]
    → 指定 M4 为绝对路径（同 ball 先例，用 conan m4/1.4.19 工具包）
  - configure.ac 无 AC_CANONICAL_HOST，显式传 --build/--host 三元组
    （config.sub 支持 *-linux-ohos），避免 config.guess 探测失败

License: GPL-3.0-or-later
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


def _prepare_autotools_env():
    """系统 automake/aclocal 硬编码不存在的 autoconf/autom4te/sed 绝对路径，
    用 shutil.which 定位 PATH 上实际可用的工具（abiword-plugin-* 先例）。"""
    for tool, var in (("autoconf", "AUTOCONF"),
                      ("autoheader", "AUTOHEADER"),
                      ("autom4te", "AUTOM4TE"),
                      ("sed", "SED")):
        if os.environ.get(var):
            continue
        path = shutil.which(tool)
        if path:
            os.environ[var] = path


def _drop_umask_077(path):
    """E114: HMDFS 对目录强制 setgid，configure 中 `umask 077 && mktemp -d`
    产生 drwx--S--- 不可写目录，config.status 无法写入 → 剥离 umask 077
    （abiword-plugin-wikipedia/3.0.8 同款修复）。"""
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    data = data.replace(
        'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
        'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`')
    data = data.replace('(umask 077 && mkdir "$tmp")', 'mkdir "$tmp"')
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)


class MftermConan(ConanFile):
    name = "mfterm"
    version = "1.0.7"
    description = "Terminal interface for working with Mifare Classic RFID tags (libnfc based)"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/4zm/mfterm"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: 判断必须同时考虑 Linux 与 OHOS 两种取值
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("mfterm is supported only on Linux/OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def requirements(self):
        # 三个依赖均已发布制品仓（W0/R36：conan list 核验通过）
        self.requires("libnfc/1.8.0")
        self.requires("readline/8.3")
        # configure.ac 用 DES_set_key_unchecked 实现 Crypto-1 CBC-MAC：
        # OpenSSL 3.x 保留（弃用告警由补丁 pragma 抑制），4.x 移除 → 锁 3.x
        self.requires("openssl/3.5.6")

    def build_requirements(self):
        # GitHub tag 归档无 configure，按上游 autogen.sh 自举
        # E178: CI worker 无 aclocal（autoreconf 报 "Can't exec aclocal"）→
        # automake/1.18 经 tool_requires 提供 aclocal/automake（其
        # package_info 以 buildenv_info 注入 PATH/ACLOCAL_PATH/PERL5LIB，
        # aircrack-ng/1.7 先例）；autoconf 侧工具仍用系统自带
        # bison/flex/m4 用 conan 包（mfterm 构建期生成 parser 代码）
        # flex 选 2.6.4.2：其 package_info 用 buildenv_info.prepend_path
        # 把 flex 注入构建 PATH（2.6.4 无此注入且缓存包缺 bin/flex）
        self.tool_requires("automake/1.18")
        self.tool_requires("bison/3.8.2")
        self.tool_requires("flex/2.6.4.2")
        self.tool_requires("m4/1.4.19")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        _prepare_autotools_env()
        tc = AutotoolsToolchain(self)
        # 上游 AM_CFLAGS: -g -Wall -Wconversion -std=c99 -Werror 全部保留。
        # OHOS clang 包装器向所有编译步骤注入 -Wl,--code-sign，-c 阶段
        # 触发 unused-command-line-argument 告警与 -Werror 冲突 → 仅放行
        # 这一个告警，其余 -Werror 语义不动。
        if self.settings.os == "OHOS":
            tc.extra_cflags.append("-Wno-error=unused-command-line-argument")
            # m4/1.4.19 范式：profile 的 tools.build:compiler_executables 与
            # [buildenv] CONFIG_SHELL 在部分 worker 上不存在（本机
            # /data/service/hnp/bin/{clang,bash} 均缺失），经 toolchain
            # environment() 用校验过的工具路径覆盖（写进
            # conanautotoolstoolchain.sh，聚合 conanbuild.sh 中排在
            # conanbuildenv-*.sh 之前，优先生效）
            env = tc.environment()
            env.define("CONFIG_SHELL", self._select_shell())
            env.define("SHELL", self._select_shell())
            # flex/2.6.4 包是 library 型（cpp_info.libs=["fl"]），不像
            # bison 那样向构建环境贡献 PATH（AutotoolsToolchain 脚本也
            # 不导出 PATH）→ 在 _configure/_make 命令前缀显式注入（见
            # _flex_path_prefix）
            cc = self._select_tool_command(["clang", "gcc", "cc"])
            if cc:
                env.define("CC", cc)
            cxx = self._select_tool_command(["clang++", "g++", "c++"])
            if cxx:
                env.define("CXX", cxx)
            for variable, candidates in {
                "LD": ["ld.lld", "ld"],
                "AR": ["llvm-ar", "ar"],
                "RANLIB": ["llvm-ranlib", "ranlib"],
                "NM": ["llvm-nm", "nm"],
            }.items():
                command = self._select_tool_command(candidates)
                if command:
                    env.define(variable, command)
            tc.generate(env=env)
        else:
            tc.generate()
        # AutotoolsDeps 注入依赖的 CPPFLAGS/LDFLAGS/LIBS（-lnfc -lusb
        # -lusb-1.0 -lcrypto …），configure 的 nfc_open/readline/libcrypto
        # 链接检查与后续 make 链接都依赖这些 flags（libnfc-tools 范式；
        # libnfc 静态包需完整传递闭包才能通过 configure 检查）
        deps = AutotoolsDeps(self)
        deps.generate()
        # configure 编译的 conftest 需在运行时加载 libusb-1.0.so.0 等
        # conan 包动态库（本 worker 无系统 libusb）→ 构建期注入
        # LD_LIBRARY_PATH（libnfc/1.8.0 配方 save_script 同款）
        env2 = Environment()
        libdirs = set()
        for dep in self.dependencies.host.values():
            for d in dep.cpp_info.aggregated_components().libdirs:
                libdirs.add(d)
        for libdir in sorted(libdirs):
            env2.prepend_path("LD_LIBRARY_PATH", libdir)
        env2.vars(self).save_script("mfterm-build-env")

    @staticmethod
    def _select_tool_command(candidates):
        for candidate in candidates:
            command = shutil.which(candidate)
            if command:
                return command
        return candidates[0] if candidates else None

    def _flex_path_prefix(self):
        """Explicitly expose Conan bison/flex tools to configure and make."""
        bins = []
        for dep in ("bison", "flex"):
            try:
                pkg = self.dependencies.build[dep].package_folder
            except KeyError:
                continue
            bindir = os.path.join(pkg, "bin")
            if os.path.isdir(bindir):
                bins.append(bindir)
        if not bins:
            return ""
        return "PATH=%s:$PATH " % ":".join(shlex.quote(x) for x in bins)

    def _tool_env_prefix(self):
        """make 阶段代码生成工具的运行环境前缀（优先级高于一切脚本 export）：
        - flex bin → PATH
        - BISON_PKGDATADIR/M4 → make 会再次调用 bison 生成 spec_parser，
          conan bison/3.8.2 以 --prefix= 构建，内置 pkgdatadir 指向不存在
          的 /share/bison（m4sugar.m4 加载失败）；OHOS 上 bison spawn m4
          传空 argv[0] → M4 指定为绝对路径（ball/1.5.0 先例）
        """
        prefix = self._flex_path_prefix()
        try:
            bison_pkg = self.dependencies.build["bison"].package_folder
        except KeyError:
            return prefix
        bison_share = os.path.join(bison_pkg, "share", "bison")
        if os.path.isdir(bison_share):
            prefix += "BISON_PKGDATADIR=%s " % shlex.quote(bison_share)
        try:
            m4_pkg = self.dependencies.build["m4"].package_folder
            m4_bin = os.path.join(m4_pkg, "bin", "m4")
            if os.path.isfile(m4_bin):
                prefix += "M4=%s " % shlex.quote(m4_bin)
        except KeyError:
            pass
        return prefix

    def build(self):
        apply_conandata_patches(self)
        self._run_bootstrap()
        self._run_configure()
        # E074: HMDFS 并行 make 触发 jobserver fifo EPERM → -j1；
        # 命令前缀注入 flex bin 与 BISON_PKGDATADIR/M4（bison 在 make
        # 阶段被再次调用生成 parser，见 _tool_env_prefix）
        self.run("%smake -j1" % self._tool_env_prefix(),
                 cwd=self.build_folder, env=self._build_env())

    def package(self):
        # Makefile.am: bin_PROGRAMS = mfterm。AutotoolsToolchain 默认
        # --prefix=/ 且 DESTDIR=package_folder（conan Autotools.install
        # 同款语义），产物落 package_folder/bin/mfterm；man 页不打包
        # （application 只需 bin/mfterm）
        self.run("%smake install DESTDIR=%s" % (self._tool_env_prefix(),
                                                shlex.quote(self.package_folder)),
                 cwd=self.build_folder, env=self._build_env())
        share = os.path.join(self.package_folder, "share")
        if os.path.isdir(share):
            shutil.rmtree(share, ignore_errors=True)

    def package_info(self):
        # 命令行工具，无库导出（m1ddc/libnfc-tools 同款）
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        bindir = os.path.join(self.package_folder, "bin")
        self.buildenv_info.append_path("PATH", bindir)
        self.runenv_info.append_path("PATH", bindir)

    def _build_env(self):
        """self.run() 的 env 参数。conan 2.29 的聚合 conanbuild.sh 依次 source
        conanautotoolstoolchain.sh（CC/CFLAGS/LDFLAGS，AutotoolsToolchain
        生成）与 conanbuildenv-*.sh（PATH，含 bison/flex/m4 工具包 bin），
        单个 "conanbuild" 即完备（lzip 包构建产物实锚）。R33：编译器从
        Toolchain env 获取，不依赖未定义 shell 变量。"""
        return "conanbuild"

    def _select_shell(self):
        """configure 生成的 Makefile 会缓存 CONFIG_SHELL。ohos-aarch64
        profile 写死的 /data/service/hnp/bin/bash 在部分 worker 上不存在
        （本机实测 ls 报 No such file），候选回退（m4/1.4.19 同款）。"""
        for shell in (os.environ.get("CONFIG_SHELL"),
                      os.environ.get("SHELL"),
                      "/data/service/hnp/bin/bash",
                      "/bin/sh",
                      "/system/bin/sh"):
            if not shell:
                continue
            if os.path.isabs(shell):
                if os.path.isfile(shell) and os.access(shell, os.X_OK):
                    return shell
            elif shutil.which(shell):
                return shell
        return "sh"

    def _run_bootstrap(self):
        """按上游 autogen.sh 自举：AUTOMAKE="automake --foreign"（上游无
        ChangeLog/NEWS 等必需文件，gnu 严格模式会失败）。

        automake/aclocal 用绝对路径钉死在 conan automake/1.18 包上：裸命令名
        "automake" 按 PATH 解析到系统 automake 1.16.5，而 ACLOCAL 已是 conan
        1.18 → aclocal.m4 由 1.18 生成、automake 1.16.5 处理，报
        "version mismatch. This is Automake 1.16.5 ... comes from Automake
        1.18"（exit 63）。ACLOCAL 一并显式指定，防环境脚本顺序变化。

        bison 运行期两个 OHOS 特有问题（ball/1.5.0 先例）：
        - conan bison/3.8.2 以 --prefix= 构建，内置 pkgdatadir 指向不存在的
          /share/bison → BISON_PKGDATADIR 重定向到包内实际位置
        - bison spawn m4 时传空 argv[0]（"A NULL argv[0] was passed
          through an exec system call"）→ M4 指定为绝对路径
        """
        _prepare_autotools_env()
        automake_pkg = self.dependencies.build["automake"].package_folder
        bison_pkg = self.dependencies.build["bison"].package_folder
        m4_pkg = self.dependencies.build["m4"].package_folder
        bison_share = os.path.join(bison_pkg, "share", "bison")
        if not os.path.isdir(bison_share):
            # 兜底：从 PATH 上的 bison 推导（部分布局包内无 share/）
            bison_bin = shutil.which("bison")
            if bison_bin:
                cand = os.path.join(os.path.dirname(os.path.dirname(bison_bin)), "share", "bison")
                if os.path.isdir(cand):
                    bison_share = cand
        m4_bin = os.path.join(m4_pkg, "bin", "m4")
        if not os.path.isfile(m4_bin):
            m4_bin = shutil.which("m4")
            if not m4_bin:
                raise ConanException("m4 not found (tool_requires m4/1.4.19)")

        automake_bin = os.path.join(automake_pkg, "bin", "automake")
        aclocal_bin = os.path.join(automake_pkg, "bin", "aclocal")
        if not (os.path.isfile(automake_bin) and os.path.isfile(aclocal_bin)):
            raise ConanException(
                "automake/aclocal not found (tool_requires automake/1.18)")

        env_cmd = (
            'AUTOMAKE="%s --foreign" ACLOCAL=%s '
            'BISON_PKGDATADIR=%s M4=%s autoreconf -fi'
            % (automake_bin, shlex.quote(aclocal_bin),
               shlex.quote(bison_share), shlex.quote(m4_bin))
        )
        self.run(env_cmd, cwd=self.source_folder, env=self._build_env())

        if self.settings.os == "OHOS":
            # E114: 剥离生成的 configure 中 umask 077（HMDFS setgid 问题）
            _drop_umask_077(os.path.join(self.source_folder, "configure"))

    def _run_configure(self):
        _prepare_autotools_env()
        configure = os.path.join(self.source_folder, "configure")
        # R33: CC/CFLAGS/LDFLAGS/LIBS 全部由聚合 conanbuild 环境注入
        # （conanautotoolstoolchain.sh + conanbuildenv-*.sh）。
        # --prefix=/ 与 DESTDIR=package_folder 组合（conan Autotools
        # 标准语义）→ 产物直接落 package_folder/bin/mfterm。
        args = ["--prefix=/"]
        env_prefix = self._flex_path_prefix()
        if self.settings.os == "OHOS":
            # configure.ac 无 AC_CANONICAL_HOST，显式传 --build/--host 三元组
            # 绕开 config.guess 对 HarmonyOS 的探测失败（config.sub 支持
            # *-linux-ohos；同 m4/1.4.19 配方做法）。
            triplet = self._ohos_triplet()
            args += ["--build=%s" % triplet, "--host=%s" % triplet]
            # profile [buildenv] 的 CONFIG_SHELL 在部分 worker 不存在
            # （configure re-exec 会 127）；用校验过的 shell 命令行前缀
            # 覆盖（前缀 env 优先级高于脚本 export）
            shell = self._select_shell()
            env_prefix += "CONFIG_SHELL=%s SHELL=%s " % (shlex.quote(shell),
                                                         shlex.quote(shell))
        self.run(
            "%s%s %s" % (env_prefix, shlex.quote(configure), " ".join(args)),
            cwd=self.build_folder,
            env=self._build_env(),
        )

    @staticmethod
    def _ohos_triplet():
        return "aarch64-unknown-linux-ohos"
