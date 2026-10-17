#!/usr/bin/env python3
"""Conan recipe for cdrskin 1.5.9 — cdrecord 兼容刻录前端（libburn 套件）。

cdrskin（libburnia 项目，scdbackup 官方站发布）是 cdrecord 的
兼容 CLI 刻录工具（C），autotools 构建。上游最新 1.5.9——清单
1.0.0 与上游不符，按用户指示用真实版本 1.5.9。

关键：cdrskin-1.5.9 tarball 是 **libburn 套件本体**
（AC_INIT([libburn],[1.5.9])，内置 libburn/ 库源码）——自带
libburn 库，**无需外部 libburn 制品**（与 cdw 依赖外部 burn 缺失
不同，本库无此缺口）。

Upstream: https://scdbackup.sourceforge.io/cdrskin-1.5.9.tar.gz

Build:   autotools（configure + make）。依赖 pthread（系统）；
         可选 libcdio（configure AC_CHECK_HEADER 检测到才用，
         无则 LIBCDIO_DEF 空——可绕过，不 requires）。
Install: bin/cdrskin + man。
Type:   application（CLI 工具——commands.json 软件级声明）

上游测试: test/（libburner/offst_source/telltoc/dewav/fake_au/poll
         ——noinst_PROGRAMS 随 make 构建）。libburner/telltoc/
         open-cd-excl 需光驱设备（OHOS 无光驱——如实记录）；
         dewav/fake_au/poll 为纯工具可实跑。
"""
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


class CdrskinConan(ConanFile):
    name = "cdrskin"
    version = "1.5.9"
    description = "Command line CD/DVD/BD burning tool (cdrecord compatible)"
    license = "GPL-2.0"
    homepage = "https://scdbackup.sourceforge.io/cdrskin_eng.html"
    url = "https://scdbackup.sourceforge.io/"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    # 无 Conan 依赖：pthread 系统库 + 内置 libburn（libcdio 可选绕过）

    def export_sources(self):
        from conan.tools.files import export_conandata_patches
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # cdrskin tarball 顶层为 ./cdrskin-1.5.9/（带 ./ 前缀）致
        # strip_root 未生效（源码落在 cdrskin-1.5.9/ 子目录，configure
        # 找不到）——手动剥离一层
        import shutil
        sub = os.path.join(self.source_folder, "cdrskin-1.5.9")
        if os.path.isdir(sub):
            for f in os.listdir(sub):
                shutil.move(os.path.join(sub, f), self.source_folder)
            os.rmdir(sub)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 老 config.guess 不识 HarmonyOS——显式 build 三元组
        # （catdoc/boa/ccze 同款）
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.generate()

    def build(self):
        from conan.tools.files import apply_conandata_patches
        apply_conandata_patches(self)
        # confstat 机制用 `umask 077 && mktemp -d ./confXXXXXX` 创建
        # 0700 临时目录做 config 文件生成——OHOS HMDFS 上 0700 目录
        # 对构建进程不可写（catdoc/boa/ccze 同款）——patch umask 077→000
        cf = os.path.join(self.source_folder, "configure")
        with open(cf, "r", encoding="utf-8", errors="replace") as f:
            s = f.read()
        s = s.replace("(umask 077 && mktemp -d \"./confXXXXXX\")",
                      "(umask 000 && mktemp -d \"./confXXXXXX\")")
        s = s.replace("(umask 077 && mkdir \"$tmp\")",
                      "(umask 000 && mkdir \"$tmp\")")
        with open(cf, "w", encoding="utf-8") as f:
            f.write(s)
        autotools = Autotools(self)
        autotools.configure()
        # configure 在 build_folder 生成 Makefile——make 默认 cwd 即
        # build_folder；-j1 绕 OHOS 禁 mkfifo jobserver（catdoc/boa 同款）
        self.run("make -j1", env="conanbuild")

    def package(self):
        # make install 装 bin/cdrskin + man
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.output.info("cdrskin 1.5.9: bin/cdrskin")
        self.conf_info.define("user.tools.cdrskin:exe", "cdrskin")
