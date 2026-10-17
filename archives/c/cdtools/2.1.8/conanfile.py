#!/usr/bin/env python3
"""Conan recipe for cdtools 2.1.8 — CD-ROM 音频控制工具集（C）。

cdtools（上游项目名 cdtool）是命令行控制 CD-ROM 音频功能的工具集
（cdplay/cdstop/cdeject/cdshuffle/cdctrl 等，单程序多名字）。版本
2.1.8 为上游真实最新版（用户给 1.0.0 不合法——按真实版 2.1.8，
2006-08-09 发布）。

Upstream: http://hinterhof.net/cdtool/dist/cdtool-2.1.8.tar.gz

Build:   autotools（configure + make）。依赖 socket（libc 自带）+
         getopt.h/mntent.h/linux/cdrom.h（OHOS sysroot 全有）——
         零第三方 Conan 依赖。
Install: bin/cdtool（cddown/cdctrl/cdtool2cddb 等，装 bin + man）。
Type:   application（CLI 工具——commands.json 软件级声明）

上游测试: 无独立测试目录（cdtool 是 CD-ROM 音频控制工具，运行需光驱
         ——OHOS 无，如实记录）。cdtool --version 可真实运行验证。
"""
import os

from conan import ConanFile
from conan.tools.files import get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class CdtoolsConan(ConanFile):
    name = "cdtools"
    version = "2.1.8"
    description = "CD-ROM audio control tools (cdtool, cdplay/cdctrl etc.)"
    license = "GPL-2.0"
    homepage = "https://hinterhof.net/cdtool/"
    url = "https://hinterhof.net/cdtool/"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    # 零第三方依赖（socket 系统库 + 系统头，OHOS sysroot 全有）

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        # confstat 机制用 `umask 077 && mktemp -d ./confstatXXXXXX` 创建
        # 0700 临时目录做 config 文件生成——OHOS HMDFS 上 0700 目录对构建
        # 进程不可写（cdrdao/catdoc/boa/ccze 同款，config.status Permission
        # denied）——patch umask 077→000
        cf = os.path.join(self.source_folder, "configure")
        with open(cf, "r", encoding="utf-8", errors="replace") as f:
            s = f.read()
        s2 = s.replace('tmp=`(umask 077 && mktemp -d -q "./confstatXXXXXX") 2>/dev/null`',
                       'tmp=`(umask 000 && mktemp -d -q "./confstatXXXXXX") 2>/dev/null`')
        s2 = s2.replace("(umask 077 && mkdir $tmp)",
                        "(umask 000 && mkdir $tmp)")
        if s2 != s:
            with open(cf, "w", encoding="utf-8") as f:
                f.write(s2)
        # commands.c 的 open() 用 O_NONBLOCK 但没 include <fcntl.h>——
        # OHOS musl 在默认模式下 O_NONBLOCK 未声明（fcntl.h 有定义但
        # 未包含）→ use of undeclared identifier。补 #include <fcntl.h>
        cmdf = os.path.join(self.source_folder, "commands.c")
        with open(cmdf, "r", encoding="utf-8", errors="replace") as f:
            s = f.read()
        s2 = s.replace('#include <stdio.h>\n#include <unistd.h>',
                       '#include <stdio.h>\n#include <fcntl.h>\n#include <unistd.h>')
        if s2 != s:
            with open(cmdf, "w", encoding="utf-8") as f:
                f.write(s2)
        # cdown.c 自定义 `char *getline(void)`（CDDB 网络读取）与 OHOS musl
        # stdio.h 的 `ssize_t getline(char**, size_t*, FILE*)`（POSIX.1-2008）
        # 冲突（conflicting types + too few arguments）——改名为 cdtool_getline
        # （定义 + 全部调用点，避免与系统 getline 冲突）
        cdownf = os.path.join(self.source_folder, "cdown.c")
        with open(cdownf, "r", encoding="utf-8", errors="replace") as f:
            s = f.read()
        s2 = s.replace("char *getline(void) {", "char *cdtool_getline(void) {")
        s2 = s2.replace("= getline();", "= cdtool_getline();")
        s2 = s2.replace("buffer = getline(),", "buffer = cdtool_getline(),")
        s2 = s2.replace("getline() have the \\r", "cdtool_getline() have the \\r")
        if s2 != s:
            with open(cdownf, "w", encoding="utf-8") as f:
                f.write(s2)
        # OHOS /tmp 只读——configure 的 ac_link 编译测试（cc 冒烟）写 /tmp
        # 失败会卡死（cdrecord 同款教训）——TMPDIR 指向可写 build 目录
        self.run("cd %s && TMPDIR=%s && ./configure --prefix=/ "
                 "--bindir=${prefix}/bin --mandir=${prefix}/share/man"
                 % (self.source_folder, self.build_folder), env="conanbuild")
        # -j1 绕 OHOS 禁 mkfifo jobserver（catdoc/boa 同款）
        self.run("cd %s && TMPDIR=%s && make -j1"
                 % (self.source_folder, self.build_folder), env="conanbuild")

    def package(self):
        self.run("cd %s && TMPDIR=%s && make install DESTDIR=%s -j1"
                 % (self.source_folder, self.build_folder,
                    self.package_folder), env="conanbuild")

    def package_info(self):
        self.output.info("cdtools 2.1.8: bin/cdtool")
        self.conf_info.define("user.tools.cdtools:exe", "cdtool")
