#!/usr/bin/env python3
"""Conan recipe — msdl 1.2.7-r2 (Media Stream DownLoader, autotools, 纯 C)

msdl 是多媒体流下载器（HTTP/FTP/RTSP/MMS/MMST/MMSH/SDP），2010 年的纯 C
代码，无外部库依赖（libc + POSIX socket），bin_PROGRAMS 仅 msdl 一个。

OHOS 适配（路径 A 基础适配，无补丁文件，全部内联完成）:
1. E129（复用知识库既有条目，不新增）: HMDFS 新建目录恒置 setgid 位，
   configure 的 `(umask 077 && mkdir/mktemp -d)` 产出 `drwx--S---` 目录
   （属主无 x 位）→ config.status "could not setup config files
   machinery"。修复: configure 内 `umask 077` → `umask 022`（VPATH 构建
   已实证生成的 config.status 自动继承 022）。
2. -fcommon: display.h/asmrule.h/rmff.h 内未初始化全局变量
   （colors_available/display_flags/symbols/operators 等 tentative
   definitions），clang 15 默认 -fno-common → ld.lld duplicate symbol。
3. -fgnu89-inline: url.h:63 `inline` 函数无分离 extern 定义，C99 inline
   语义下 is_url_valid_char 无外部定义 → ld.lld undefined symbol。

native 编译（本机即 HarmonyOS PC），不传 --build/--host/--target 三元组
（E129 禁止项）；平台探测走 configure 自带 config.guess（识别为
aarch64-unknown-linux-ohos，已实证）。
"""
import os
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class MsdlConan(ConanFile):
    name = "msdl"
    version = "1.2.7-r2"
    description = "Media Stream DownLoader: a downloader for multimedia streams " \
                  "(HTTP/FTP/RTSP/MMS/MMST/MMSH/SDP) written in C"
    license = "GPL-2.0-or-later"
    url = "https://gitlab.atomgit.com/openharmony-tpc/oh_ap_baker"
    homepage = "http://msdl.sourceforge.net/"
    topics = ("downloader", "streaming", "mms", "rtsp", "ftp", "http", "multimedia")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    # 上游 2010 年纯 C 代码，无外部库依赖（libc + POSIX socket）

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"msdl is adapted for Linux/OHOS, got {self.settings.os}"
            )
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                f"msdl/1.2.7-r2 is validated for OHOS armv8, got {self.settings.arch}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # --- 2010 老代码的链接语义（仓库先例: -fcommon 见 barcode/0.99,
        #     -fgnu89-inline 见 mlddc/1.0.1）--------------------------------
        # 不区分 OS 追加: 两个 flag 对新 gcc/clang 无副作用，且保持 Linux
        # 本地验证与 OHOS CI 行为一致。
        tc.extra_cflags.extend(["-fcommon", "-fgnu89-inline"])
        tc.generate()

    def build(self):
        # --- E129 修复（知识库既有条目，方案复用，不新增条目）---------------
        # HMDFS（HarmonyOS 分布式文件系统）新建目录恒置 setgid，configure 的
        # `umask 077 && mktemp/mkdir` 产生的临时目录模式为 drwx--S---，
        # 属主亦无 x 位 → permission denied → "could not setup config files
        # machinery"。umask 077 → 022 已在本机实证修复（详见 notes.md）。
        # VPATH 构建下 configure 生成的 config.status 自动继承 022，
        # 故只需替换 configure 一处（共 2 处 umask 077）。
        configure = os.path.join(self.source_folder, "configure")
        replace_in_file(self, configure, "umask 077", "umask 022")

        # HMDFS 某些路径会剥掉可执行位；恢复之，保证 ./configure 可运行
        # （barcode/0.99 同款防御）。
        if os.path.isfile(configure):
            mode = os.stat(configure).st_mode
            os.chmod(configure, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # 源码 COPYING 放的是 GPLv3 全文，但 24 个 src/*.c 头部均为
        # "version 2 ... or (at your option) any later version"，许可证以
        # 源文件头为准（GPL-2.0-or-later，详见 notes.md）。
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # 纯 CLI 工具：无可链接库目标，仅声明 bin 目录（R38 commands.json 配套）
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
