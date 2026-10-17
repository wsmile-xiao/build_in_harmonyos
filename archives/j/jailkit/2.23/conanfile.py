#!/usr/bin/env python3
"""Conan recipe — jailkit 2.23 (autotools 预生成 configure; C 工具 + Python 脚本套件)

jailkit 是 chroot 监禁工具套件：C 二进制（jk_socketd/jk_chrootsh/
jk_chrootlaunch/jk_lsh/jk_uchroot）+ Python 运维脚本（jk_init/jk_cp/
jk_check/jk_jailuser/jk_list/jk_update + jk_lib.py）+ /etc/jailkit ini
配置 + man 页。所有解析器（iniparser/passwdparser/wordexp）随源码捆绑，
无外部 conan 依赖。

OHOS 适配要点（R32/R33/R9/E074/E114；先例 zzuf/0.15 + gtypist/2.10.1）：
1. 官方 tarball 自带预生成 configure（autoconf 2.72）→ 无需 bootstrap；
   configure.ac 无 AC_CANONICAL_*，不需要 config.guess/--build。
2. 构建体系：根 Makefile 递归 src/py/man 三个手写 Makefile（非 automake），
   in-source 构建；无 test/check 目标 —— 上游测试为 src/ 两个自检程序
   （iniparsertester/passwdparsertester，有 make 规则但不在 all），在
   build() 显式构建并运行、断言关键输出。
3. configure 硬依赖 python（AC_PATH_PROG 找 `python`，找不到即报错）；
   真机 python3 在 HNP 路径 → 用 AC_ARG_VAR 覆盖
   PYTHONINTERPRETER=/data/service/hnp/bin/python3（存在性探测后传入）。
   py/Makefile 用它重写脚本 shebang 并 py_compile jk_lib。
4. 可选依赖 libcap/procmail 未命中自动跳过（HAVEPROCMAIL 置 # 注释掉
   jk_procmailwrapper），不引入 conan 依赖。
5. 顶层 make install 会向 /etc/shells 追加 jk_chrootsh 行（test -w 守卫）
   —— 真机不应改系统路径 → package() 复刻顶层 install 的 ini/src/py/man
   四段到 package_folder，跳过 /etc/shells 写段。
6. setuid 4755 安装位（jk_chrootsh/jk_uchroot）为上游语义，保留安装命令；
   HMDFS 忽略 chmod（E114 族）不影响文件落包。
7. E114: configure/config.status 内部 umask 077 临时目录 → 生成脚本
   077→022 替换，命令前置 umask 022；§12.38① CONFIG_SHELL 缺陷 →
   env -u CONFIG_SHELL SHELL=/bin/sh + 绝对路径。
8. E074: HMDFS jobserver fifo EPERM → make -j1。
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class JailkitConan(ConanFile):
    name = "jailkit"
    version = "2.23"
    description = ("jailkit - chroot jail utilities (jk_socketd/jk_chrootsh/"
                   "jk_lsh/jk_init/jk_cp and friends)")
    # 主体 modified BSD（BSD-3-Clause 同族）；捆绑的 src/wordexp.{c,h} 为
    # GNU Library GPL —— 覆盖整个包用 AND 组合
    license = "BSD-3-Clause AND LGPL-2.0-or-later"
    homepage = "https://olivier.sessink.nl/jailkit/"
    url = "https://olivier.sessink.nl/jailkit/"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        # 根 Makefile 递归子目录手写 Makefile，以相对路径编译 —— in-source
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # E490: 确保 configure 保留可执行位（真机一律 sh 显式调用）
        p = os.path.join(self.source_folder, "configure")
        if os.path.exists(p):
            os.chmod(p, 0o755)

    def validate(self):
        # R32: settings.os 判断必须同时接受 Linux 与 OHOS
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "jailkit OHOS adaptation is validated on Linux/OHOS, not "
                + str(self.settings.os))

    def requirements(self):
        # W0: 全部解析器/wordexp 随源码捆绑，无外部库依赖；libcap/procmail
        # 为上游可选（未命中自动跳过）；python3 为设备 HNP 自带运行时
        # （build 期探测，见文件头 #3）。
        # MateBook 第一步：本任务无 conan 依赖，R35 检查为空集。
        pass

    def generate(self):
        # 编译器经 profile tools.build:compiler_executables 注入 conanbuild env
        AutotoolsToolchain(self).generate()

    def _python3(self):
        cand = "/data/service/hnp/bin/python3"
        return cand if os.path.isfile(cand) else "python3"

    def build(self):
        apply_conandata_patches(self)

        # E114: configure/config.status 内部以 umask 077 创建临时目录，
        # HMDFS 上组无写位导致写入失败 → 生成脚本替换（平台适配，非源码补丁）
        for script in ("configure", "config.status"):
            path = os.path.join(self.source_folder, script)
            if os.path.exists(path):
                with open(path) as f:
                    content = f.read()
                content = content.replace("umask 077", "umask 022")
                with open(path, "w") as f:
                    f.write(content)

        src = self.source_folder.replace("\\", "/")
        prefix = self.package_folder.replace("\\", "/")
        # §12.38①: env -u CONFIG_SHELL SHELL=/bin/sh + 绝对路径；
        # PYTHONINTERPRETER 经 AC_ARG_VAR 显式覆盖（上游只找 `python`）
        self.run(
            f'umask 022 && env -u CONFIG_SHELL SHELL=/bin/sh '
            f'sh "{src}/configure" --prefix="{prefix}" '
            f'PYTHONINTERPRETER={self._python3()}',
            env="conanbuild",
        )
        # E074: HMDFS jobserver fifo EPERM → make -j1（all = src/py/man）
        self.run(
            f'umask 022 && env -u CONFIG_SHELL SHELL=/bin/sh '
            f'make -C "{src}" -j1',
            env="conanbuild",
        )

        # 上游自检程序（Makefile 有规则、不在 all）：显式构建并运行，
        # 关键输出断言（iniparser/passwdparser 是整个套件的基础组件）
        self.run(
            f'umask 022 && env -u CONFIG_SHELL SHELL=/bin/sh '
            f'make -C "{src}/src" iniparsertester passwdparsertester',
            env="conanbuild",
        )
        ini_log = os.path.join(self.build_folder, "iniparser-selftest.log")
        self.run(
            f'cd "{src}/src" && ./iniparsertester > "{ini_log}" 2>&1',
            env="conanbuild",
        )
        with open(ini_log, encoding="utf-8", errors="replace") as fh:
            ini_out = fh.read()
        if not ini_out.strip():
            raise ConanException("iniparsertester produced no output")
        pw_log = os.path.join(self.build_folder, "passwdparser-selftest.log")
        # 与 iniparsertester 同型：passwdparsertester 用相对路径读
        # passwdparsertester.test，必须在 src/ 内运行（真机第 2 轮实测
        # 绝对路径调用报 "found nothing"）
        self.run(
            f'cd "{src}/src" && ./passwdparsertester > "{pw_log}" 2>&1',
            env="conanbuild",
        )
        with open(pw_log, encoding="utf-8", errors="replace") as fh:
            pw_out = fh.read()
        # passwdparsertester.test 的 uid 100 行末尾无换行 —— 覆盖该解析分支
        if "found user jaja!" not in pw_out:
            raise ConanException(
                f"passwdparsertester unexpected output: {pw_out.strip()!r}")

    def package(self):
        src = self.source_folder.replace("\\", "/")
        prefix = self.package_folder.replace("\\", "/")
        # 复刻顶层 install 的四段（ini/src/py/man），跳过其向 /etc/shells
        # 追加的系统路径写段（真机包内容只落 package_folder）
        iniprefix = f"{prefix}/etc/jailkit"
        self.run(
            f'umask 022 && mkdir -p "{iniprefix}" && '
            f'for f in "{src}"/ini/*.ini; do '
            f'cp "$f" "{iniprefix}/" || exit 1; done',
            env="conanbuild",
        )
        for sub in ("src", "py", "man"):
            self.run(
                f'umask 022 && env -u CONFIG_SHELL SHELL=/bin/sh '
                f'make -C "{src}/{sub}" install',
                env="conanbuild",
            )

    def package_info(self):
        # R38: 套件提供多个 jk_* 命令（软件级 commands.json 已声明）
        self.cpp_info.bindirs = ["bin", "sbin"]
