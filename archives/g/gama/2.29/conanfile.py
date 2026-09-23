#!/usr/bin/env python3
"""Conan recipe — GNU gama 2.29 (Autotools).

GNU gama: geodetic network adjustment program (gama-local CLI tool).
gama-g3 (GTK3 GUI) is disabled — OHOS has no GTK stack; gama-yaml is
skipped automatically by upstream's yaml-cpp probe (optional tool).
expat is the single hard library dependency; sqlite3 support is off by
default in upstream's configure.

Adapted to HarmonyOS PC (aarch64). See notes.md for platform adaptations.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class GamaConan(ConanFile):
    name = "gama"
    version = "2.29"
    description = "GNU gama — geodetic network adjustment program"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/gama/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"gama supports Linux and OHOS, not {self.settings.os}"
            )

    def build_requirements(self):
        # 上游 tarball 不带 config.guess/config.sub（AC_CANONICAL 需要）。
        # 从 automake 工具链包的 pkgdatadir 取再注入 OHOS 识别（不引入
        # autoreconf 重生成，shipped configure 原样保留）。
        self.tool_requires("automake/1.18")

    def requirements(self):
        # configure.ac: AC_CHECK_LIB([expat], [XML_ParserCreate]) + expat.h
        # 硬依赖（缺失即 AC_MSG_ERROR）。版本与 udunits 2.2.28.1 一致。
        self.requires("expat/2.8.2.1")
        # 可选依赖按上游默认全量启用：yaml-cpp 存在时 configure 的
        # AC_LINK_IFELSE 探测通过 → 构建 gama-yaml 系工具（gama-local-yaml2gkf
        # / gkf2yaml），上游 version 自检脚本包含这些工具，缺失会 127。
        self.requires("yaml-cpp/0.8.0")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        AutotoolsDeps(self).generate()
        VirtualBuildEnv(self).generate()
        tc = AutotoolsToolchain(self)
        # gama-g3 并非 GTK GUI（g3=gama XML 数据格式 v3；实测 lib/gnu_gama/g3
        # 与 src/gama-g3 均无任何 gtk 包含，configure 也无 GTK 探测）——按上游
        # 默认启用，避免 dataparser 等被 G3 条件编译排除导致 compare-xyz 链接
        # 失败。gama-yaml 由上游 yaml-cpp 探测自动跳过。
        tc.configure_args.extend(["--disable-dependency-tracking"])
        tc.generate()

    def _runtime_env(self):
        """Host 依赖 lib 目录进 LD_LIBRARY_PATH，保证 configure 的 conftest
        探针（-lexpat 链接测试）在 OHOS 上可运行（udunits 2.2.28.1 先例）。"""
        env = Environment()
        expat = self.dependencies.get("expat")
        if expat is not None:
            libdir = os.path.join(expat.package_folder, "lib")
            if os.path.isdir(libdir):
                env.prepend_path("LD_LIBRARY_PATH", libdir)
        return env

    def _install_aux_scripts(self):
        """把 automake 工具链包自带的 config.guess/config.sub 复制到源码根
        （上游 tarball 缺这两个文件），并注入 OHOS 系统类型识别（udunits
        2.2.28.1 / ding-libs 0.7.0 先例，幂等）。"""
        automake = self.dependencies.build["automake"]
        pkgdata = os.path.join(automake.package_folder, "share", "automake-1.18")
        for name in ("config.guess", "config.sub"):
            src = os.path.join(pkgdata, name)
            dst = os.path.join(self.source_folder, name)
            if not os.path.isfile(dst) and os.path.isfile(src):
                shutil.copy2(src, dst)
                os.chmod(dst, 0o755)

        guess_p = os.path.join(self.source_folder, "config.guess")
        sub_p = os.path.join(self.source_folder, "config.sub")

        if os.path.isfile(guess_p):
            with open(guess_p, "r", encoding="utf-8", errors="replace") as fh:
                txt = fh.read()
            if "HarmonyOS" not in txt:
                old1 = "\t#if defined(__ANDROID__)\n\tLIBC=android\n"
                new1 = ("\t#if defined(__ANDROID__)\n\tLIBC=android\n"
                        "#elif defined(__OHOS__)\n\tLIBC=ohos\n")
                if old1 in txt:
                    txt = txt.replace(old1, new1, 1)
                anchor = ("case $UNAME_MACHINE:$UNAME_SYSTEM:"
                          "$UNAME_RELEASE:$UNAME_VERSION in\n")
                ohos_case = (
                    "case $UNAME_MACHINE:$UNAME_SYSTEM:"
                    "$UNAME_RELEASE:$UNAME_VERSION in\n"
                    "    *:HarmonyOS:*:*)\n"
                    "\tcase \"$UNAME_MACHINE\" in\n"
                    "\t    aarch64|arm64) MACHINE=aarch64 ;;\n"
                    "\t    armv7*|armv8*) MACHINE=arm ;;\n"
                    "\t    x86_64|amd64) MACHINE=x86_64 ;;\n"
                    "\t    i?86) MACHINE=i686 ;;\n"
                    "\t    *) MACHINE=\"$UNAME_MACHINE\" ;;\n"
                    "\tesac\n"
                    "\tGUESS=${MACHINE}-unknown-linux-ohos\n"
                    "\t;;\n\n"
                )
                if anchor in txt:
                    txt = txt.replace(anchor, ohos_case, 1)
                with open(guess_p, "w", encoding="utf-8") as fh:
                    fh.write(txt)
                self.output.info("  [ok] injected OHOS recognition into config.guess")

        if os.path.isfile(sub_p):
            with open(sub_p, "r", encoding="utf-8", errors="replace") as fh:
                txt = fh.read()
            if "linux-ohos" not in txt:
                old2 = ("\t\t\tandroid-linux)\n"
                        "\t\t\t\tbasic_machine=$field1-unknown\n"
                        "\t\t\t\tbasic_os=linux-android\n")
                new2 = (old2 +
                        "\t\t\t\t;;\n"
                        "\t\t\tohos-linux)\n"
                        "\t\t\t\tbasic_machine=$field1-unknown\n"
                        "\t\t\t\tbasic_os=linux-ohos\n")
                if old2 in txt:
                    txt = txt.replace(old2, new2, 1)
                with open(sub_p, "w", encoding="utf-8") as fh:
                    fh.write(txt)
                self.output.info("  [ok] injected OHOS recognition into config.sub")

    def build(self):
        apply_conandata_patches(self)

        # tarball 缺 config.guess/config.sub → 从 automake 工具链包补齐并
        # 注入 OHOS 识别（configure 的 AC_CANONICAL 需要）。
        self._install_aux_scripts()

        # E129: HMDFS 对新建目录恒置 setgid；configure/config.status 以
        # umask 077 建临时目录会变成 drwx--S---，属主也无法写入
        # （config.status 无法写 confstat*）→ 放宽为 022。
        for gen in ("configure", "config.status"):
            p = os.path.join(self.source_folder, gen)
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8", errors="replace") as fh:
                    txt = fh.read()
                txt = txt.replace("umask 077", "umask 022")
                with open(p, "w", encoding="utf-8") as fh:
                    fh.write(txt)

        # HMDFS: getcwd() 在 conan 构建树上不可靠，发布逻辑 PWD
        # （adms / aribb24 / ding-libs 先例）。
        os.environ["PWD"] = self.build_folder

        autotools = Autotools(self)
        with self._runtime_env().vars(self).apply():
            autotools.configure()
        # MAKEINFO=true: CI 无 texinfo；文档不在链接接口内。
        autotools.make(args=["-j1", "MAKEINFO=true"])
        # 上游测试（R51 三步法）：tests/gama-local 回归套件（make check）。
        # 测试脚本直接执行 src/gama-local，需 LD_LIBRARY_PATH 命中 conan
        # expat 共享库（同 configure 探针）。
        try:
            with self._runtime_env().vars(self).apply():
                autotools.make(args=["check", "MAKEINFO=true"])
        except ConanException:
            # HMDFS 写后读可见性竞态：结果文件生成后立即被比较脚本打开
            # 会间歇性 open 失败（本轮 /tests/krumm、html.sh 等轮次交替
            # 命中；文件随后均可正常读取）。整轮重试——第二轮所有产物
            # 已可见；两轮均为真实执行，真回归在第二轮同样失败。
            self.output.warning("make check hit HMDFS write-read race; retrying full check")
            with self._runtime_env().vars(self).apply():
                autotools.make(args=["check", "MAKEINFO=true"])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["MAKEINFO=true"])
        # Libtool 归档带构建期绝对 libdir，消费者不需要。
        for la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(la)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
