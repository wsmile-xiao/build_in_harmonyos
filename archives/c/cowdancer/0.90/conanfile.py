#!/usr/bin/env python3
"""Conan recipe — cowdancer 0.90.

cowdancer：Debian pbuilder 体系中的 copy-on-write 目录树工具
（cow-shell / cowdancer-ilistcreate / cowdancer-ilistdump / cowbuilder /
qemubuilder + LD_PRELOAD 库 libcowdancer.so），通过自动链接表
（ilist）实现 COW 语义，避免重复复制大目录树。

OHOS/musl 适配要点（详见 notes.md）：
  - git archive 不带 configure，build() 运行 autoreconf -fi 引导；
  - canonicalize_file_name / get_current_dir_name 为 glibc GNU 扩展，
    OHOS musl libc 缺失 → patch 替换为 realpath(x,NULL)/getcwd(NULL,0)；
  - musl 生态工具常经 openat 访问文件，cowdancer 上游只拦截 open/open64，
    COW 核心机制会被绕过 → patch 新增 openat 拦截；
  - SHM: Makefile.am SHELL=/bin/bash（OHOS 无）→ bash(PATH 查找)；
  - tests/016_memleakcheck 依赖 glibc 专用 mcheck.h，musl 缺失，从
    check_PROGRAMS 移除（上游注释也列其为 fragile 不默认运行）。
  - conan-verify 版（本档）：chunk 编译经 shm 缓存。

构建环境：
  - tool_requires automake/libtool（同 argp-standalone：CI 宿主缺 aclocal/
    libtoolize，仅 autoconf 套件在 /data/service/hnp/bin）。
  - -pr:h 与 -pr:b 均需传入（tool_requires 用 build profile 解析）。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    get, apply_conandata_patches, export_conandata_patches,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


def _prepare_autotools_env():
    """automake/libtool 安装中的 autoconf/autom4te/sed 硬编码了不存在的
    绝对路径，把环境变量指向 PATH 中实际存在的同名工具。"""
    for tool, var in (("autoconf", "AUTOCONF"),
                      ("autoheader", "AUTOHEADER"),
                      ("autom4te", "AUTOM4TE"),
                      ("sed", "SED")):
        if os.environ.get(var):
            continue
        path = shutil.which(tool)
        if path:
            os.environ[var] = path


def _drop_umask_077(conanfile, path):
    """E114: HMDFS 强制目录 setgid；`umask 077 && mktemp -d` 得到的
    drwx--S--- 目录属主自身也不可写。移除 configure 中的 umask 077，
    使 config.status 能创建临时目录。"""
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    data = data.replace(
        'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
        'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`')
    data = data.replace('(umask 077 && mkdir "$tmp")', 'mkdir "$tmp"')
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)


class CowdancerConan(ConanFile):
    name = "cowdancer"
    version = "0.90"
    description = "cowdancer copy-on-write directory tree utilities (cow-shell/cowbuilder/qemubuilder + libcowdancer LD_PRELOAD library)"
    license = "GPL-2.0-or-later"
    homepage = "https://salsa.debian.org/pbuilder-team/cowdancer"
    url = "https://salsa.debian.org/pbuilder-team/cowdancer"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # git archive 无 configure，build() 需 autoreconf -fi；CI 宿主缺
        # aclocal/libtoolize（仅 autoconf 套件），按 argp-standalone 先例
        # 用 tool_requires 补齐。tool_requires 按 build profile 解析，
        # 因此 conan create 需同时传 -pr:h 与 -pr:b。
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def validate(self):
        # R32: settings.os 必须 in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "cowdancer is only supported on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        _prepare_autotools_env()
        tc = AutotoolsToolchain(self)
        # config.guess 识别不了 HarmonyOS（uname -s=HarmonyOS），
        # 显式传入 triplet（config.sub 支持 *-linux-ohos），同 argp-standalone。
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        tc.generate()

    def build(self):
        _prepare_autotools_env()
        # git archive 无 configure：autoreconf 引导
        self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        # E114: 去掉生成的 configure 中的 umask 077（HMDFS）
        _drop_umask_077(self, os.path.join(self.source_folder, "configure"))
        autotools = Autotools(self)
        autotools.configure()
        # E074: 并行 make 会撞 HMDFS jobserver fifo EPERM
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # libcowdancer.so 经 `pkglib_LTLIBRARIES` 安装在 $(libdir)/cowdancer/，
        # 命令行工具在 bin/（cow-shell/cowdancer-ilistcreate/cowdancer-ilistdump）
        # 与 sbin/（cowbuilder/qemubuilder，R38 commands.json 已声明）。工具包以
        # 可执行文件为主，显式声明 bindirs 供消费者解析；库供需要者按需链接。
        self.cpp_info.bindirs = ["bin", "sbin"]
        self.cpp_info.libdirs = ["lib/cowdancer"]
        self.cpp_info.libs = ["cowdancer"]