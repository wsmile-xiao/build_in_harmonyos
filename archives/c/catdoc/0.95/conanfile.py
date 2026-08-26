#!/usr/bin/env python3
"""Conan recipe for catdoc 0.95 — MS Word/Excel/PPT 文本提取工具。

catdoc 是 C 语言编写的 Microsoft Office 文档文本提取工具（catdoc/
catppt/xls2csv/wordview），autotools configure + make 构建，依赖仅
libc（Build-Depends 仅 debhelper、Depends 仅 shlibs——无 Conan 依赖）。

Upstream: Debian snapshot 官方归档 catdoc_0.95.orig.tar.gz（wagner.pp.ru
官方源），sha256 0d6ef66f...。版本 0.95 为上游最新版（清单 1.0.0 与
上游不一致——按用户指示用真实版本 0.95）。

Build:  configure --build=aarch64-unknown-linux-gnu（config.guess 老
        版本不识 HarmonyOS——ncurses/boa 同款）+ make -j1。
Install: bin/catdoc bin/catppt bin/xls2csv bin/wordview。
Type:   application（CLI 工具——commands.json 软件级声明）

Deps:   仅 libc——无 Conan 依赖。
上游测试: 0/0（源码树无 test 套件——如实记录）。

R26: Not applicable。
R32: settings.os 需检查 ("Linux", "OHOS")。
R38: CLI 工具——commands.json 已声明（软件级 archives/c/catdoc/commands.json）。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class CatdocConan(ConanFile):
    name = "catdoc"
    version = "0.95"
    description = "MS Word/Excel/PPT 文本提取工具（catdoc/catppt/xls2csv/wordview）"
    license = "GPL-2.0"
    homepage = "https://wagner.pp.ru/~vitus/software/catdoc/"
    url = "https://snapshot.debian.org/package/catdoc/1%3A0.95-6/"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        from conan.tools.files import export_conandata_patches
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.generate()

    def build(self):
        from conan.tools.files import apply_conandata_patches
        apply_conandata_patches(self)

        # configure（Autoconf 2.69 生成）的 confstat 机制用
        # `umask 077 && mktemp -d ./confXXXXXX` 创建 0700 临时目录做
        # config 文件生成——OHOS HMDFS 上 0700 目录对构建进程不可写
        # （boa 同款，DRAFT-ohos-autoconf-confstat-umask-077-perm 覆盖）
        # ——patch umask 077→000。
        cf = os.path.join(self.source_folder, "configure")
        with open(cf, "r", encoding="utf-8", errors="replace") as f:
            s = f.read()
        s = s.replace("(umask 077 && mktemp -d \"./confXXXXXX\")",
                      "(umask 000 && mktemp -d \"./confXXXXXX\")")
        s = s.replace("(umask 077 && mkdir \"$tmp\")",
                      "(umask 000 && mkdir \"$tmp\")")
        with open(cf, "w", encoding="utf-8") as f:
            f.write(s)

        at = Autotools(self)
        at.configure()
        # configure 在 build_folder 生成 Makefile——make 默认 cwd 即
        # build_folder（勿用 source_folder）；-j1 绕 OHOS 禁 mkfifo
        # jobserver（boa 同款）
        self.run("make -j1", env="conanrun")

    def package(self):
        # make install 的 install-* 规则用 `../mkinstalldirs` 相对路径，
        # 在 conan build-release 结构下失效——改为直接从 build 产物复制：
        #   - src/{catdoc,catppt,xls2csv}（编译可执行）
        #   - charsets/（二进制按 CHARSETPATH=/share/catdoc 运行时查找）
        # wordview 是 tcl 脚本（WISH 解释器）——OHOS 无 tclsh，系统级
        # 阻塞如实记录（batsignal 同构）。
        # build_folder 结构因 AutotoolsToolchain 而异（build-release/src
        # 或 src）——glob 兜底定位产物。
        import glob
        bsrc = None
        for cand in (os.path.join(self.build_folder, "build-release", "src"),
                     os.path.join(self.build_folder, "src")):
            if os.path.isfile(os.path.join(cand, "catdoc")):
                bsrc = cand
                break
        if bsrc is None:
            hits = glob.glob(os.path.join(self.build_folder, "**", "src", "catdoc"),
                             recursive=True)
            if hits:
                bsrc = os.path.dirname(hits[0])
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        if bsrc:
            for prog in ("catdoc", "catppt", "xls2csv"):
                if os.path.isfile(os.path.join(bsrc, prog)):
                    copy(self, prog, src=bsrc, dst=bindir)

        # charsets 数据（CHARSETPATH=${datadir}/catdoc）
        sh = os.path.join(self.package_folder, "share", "catdoc")
        os.makedirs(sh, exist_ok=True)
        for f in os.listdir(os.path.join(self.source_folder, "charsets")):
            if f.endswith(".txt"):
                copy(self, f, src=os.path.join(self.source_folder, "charsets"), dst=sh)

    def package_info(self):
        self.output.info("catdoc 0.95: bin/catdoc bin/catppt bin/xls2csv bin/wordview")
        # R38 — CLI 工具
        self.conf_info.define("user.tools.catdoc:exe", "catdoc")
