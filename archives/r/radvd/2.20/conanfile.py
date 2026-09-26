#!/usr/bin/env python3
"""Conan recipe for radvd 2.20 — IPv6 Router Advertisement daemon (Autotools).

上游官方 release 包自带预生成 Autotools 文件（configure / Makefile.in /
aclocal.m4 / config.h.in），但**不**自带解析器生成物（无 gram.c / lex.yy.c），
`gram.y` + `scanner.l` 必须现场生成 ⇒ bison/flex 是构建期工具依赖。

平台适配点（详见 notes.md 的证据表）：
- config.guess（timestamp 2018-02-24）不识别 uname -s=HarmonyOS，configure 起手即报
  cannot guess build type ⇒ 补丁 0001 加 HarmonyOS 分支输出
  aarch64-unknown-linux-ohos（本版 config.guess 的 case 风格是 echo/exit，照抄新版
  GUESS= 变量写法会命中分支却不输出、落到 unable to guess system type 兜底）。
- config.sub（timestamp 2018-02-22）的两处 OS 白名单不含 ohos，会把该三元组判为
  Invalid configuration ⇒ 补丁 0002 补入 linux-ohos* / -linux-ohos*。上游
  configure.ac 的 arch 闸门按 *linux* 分派 ⇒ 归入 linux 分支并定义 _GNU_SOURCE
  （musl 下暴露 in6_pktinfo 必需）。
- configure 的 netlink 探测同含 <sys/socket.h> 与 <linux/netlink.h>，在 OHOS
  musl sysroot 上因 sockaddr_storage 重定义而失败（知识条目 E091/E119）⇒
  HAVE_NETLINK 未定义、netlink.o 不入 CONDITIONAL_SOURCES。这是上游
  configure.ac 自身的降级分支（AC_MSG_RESULT(no)，非硬错误）；是否值得用
  平台宏补丁强行打开，取决于运行时 netlink 是否可用——实测结论记 notes.md。
- 上游 `make check` 必须配 `--with-check`，否则 Makefile.am 的
  `check: $(error libcheck not available)` 直接失败。

产物：radvd 与 radvdump 两个可执行文件 ⇒ application 包（R38 需 commands.json）。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class RadvdConan(ConanFile):
    name = "radvd"
    version = "2.20"
    description = (
        "radvd: an implementation of the Router Advertisement and default "
        "router parts of the IPv6 Neighbor Discovery Protocol"
    )
    license = "BSD-4-Clause"
    homepage = "https://github.com/radvd-project/radvd"
    url = ""
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32：平台判断一律用 in ("Linux", "OHOS")，不得 == "Linux"。
        # 上游 configure.ac 的 arch 闸门只接受 *linux* / *bsd* / *darwin*，
        # OHOS 走 linux 分支（target 三元组含 linux）。
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "radvd upstream supports only Linux and BSD-4.4 kernels "
                f"(configure.ac arch gate); got os={self.settings.os}"
            )
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "radvd OHOS support is validated for armv8/AArch64 only"
            )

    def build_requirements(self):
        # 官方包不含预生成解析器：AC_PROG_YACC / AM_PROG_LEX 需要现场跑
        # bison -d -o gram.c gram.y 与 flex。制品仓两者均已发布（R36 已核）。
        self.tool_requires("bison/3.8.2")
        self.tool_requires("flex/2.6.4")
        # 上游单元测试框架：configure.ac 只在 --with-check 时
        # PKG_CHECK_MODULES([CHECK], [check >= 0.9.4])。
        self.test_requires("check/0.15.2")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _dep_folder(self, name, *parts):
        """在 test/host/build 三个上下文里找一个依赖的包目录片段。"""
        for ctx in (
            self.dependencies.test,
            self.dependencies.host,
            self.dependencies.build,
        ):
            try:
                dep = ctx[name]
            except KeyError:
                continue
            return os.path.join(dep.package_folder, *parts)
        return None

    def generate(self):
        # check.pc 由 PkgConfigDeps 落到 generators 目录，供 configure 的
        # PKG_CHECK_MODULES 消费；AutotoolsDeps/VirtualBuildEnv 提供 bison/flex
        # 与编译链接参数（R33：不裸用 shell 里的 CC/CFLAGS）。
        PkgConfigDeps(self).generate()
        AutotoolsDeps(self).generate()
        VirtualBuildEnv(self).generate()

        tc = AutotoolsToolchain(self)
        # 唯一偏离默认的参数：打开上游 Check 测试套件。不带它，
        # Makefile.am 的 `check:` 目标会 $(error libcheck not available)。
        tc.configure_args.append("--with-check")
        tc.generate()

    def _env(self, for_tests=False):
        env = Environment()
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        # /tmp 在目标机只读（E002），autoconf 与 libcheck 都要可写临时目录。
        tmp = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp, exist_ok=True)
        env.define("TMPDIR", tmp)
        env.define("TMP", tmp)
        env.define("TEMP", tmp)
        if for_tests:
            check_lib = self._dep_folder("check", "lib")
            if check_lib and os.path.isdir(check_lib):
                # 仅作用于 make check，不外溢到编译期链接探测。
                env.prepend_path("LD_LIBRARY_PATH", check_lib)
        return env

    def build(self):
        apply_conandata_patches(self)
        # HMDFS：构建树建好后父目录 getcwd() 不可达，configure 在
        # CONFIG_SHELL 下二次 exec 时 `pwd` 探测会报
        # "working directory cannot be determined"（ding-libs/adms 同款处置），
        # 发布逻辑 PWD 让 shell 不必调用 getcwd()。
        os.environ["PWD"] = self.build_folder
        autotools = Autotools(self)
        with VirtualBuildEnv(self).vars().apply(), self._env().vars(self).apply():
            autotools.configure()
            autotools.make(args=["-j1"])

        # VPATH 测试数据缺口（与补丁 0005 同族，这一处在数据文件而不在源码）：
        # 上游 test/util.c、test/send.c 用字面量 "test/test1.conf" 读配置，而
        # automake 的 TESTS 以**构建树**为 cwd ⇒ 外树构建时数据文件只在 source_folder/test/
        # 下，构建树 test/ 里没有它 → iface_setup 的 readin_config() 返回 NULL，
        # libcheck 连带中断后续用例（实测只跑到 17/36 并报 3 处 failure）。
        # 不动上游源码的路径写法：把测试数据 stage 进构建树，实测 36/36 全绿。
        copy(self, "*.conf", src=os.path.join(self.source_folder, "test"),
             dst=os.path.join(self.build_folder, "test"))

        # 层 1：上游官方测试（TESTS = check_all；36 个注册用例，见 MANIFEST.yml）
        with VirtualBuildEnv(self).vars().apply(), self._env(
            for_tests=True
        ).vars(self).apply():
            autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        with VirtualBuildEnv(self).vars().apply(), self._env().vars(self).apply():
            autotools.install(args=["-j1"])
        copy(self, "COPYRIGHT", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "CHANGES", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "radvd.conf.example", src=self.source_folder,
             dst=os.path.join(self.package_folder, "doc"), keep_path=False)

    def package_info(self):
        # sbin_PROGRAMS：Conan 把 sbindir 归一到 ${prefix}/bin，实测产物落点见 notes.md
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_find_mode", "none")
