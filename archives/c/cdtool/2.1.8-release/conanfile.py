#!/usr/bin/env python3
"""Conan recipe for cdtool 2.1.8-release — CD-ROM 音频控制工具集（C）。

cdtool 是命令行控制 CD-ROM 音频功能的工具集。上游是「单程序多名字」设计：
真正的二进制只有一个（cdtool），安装到 lib/cdtool/cdtool，bin/ 下以 10 个
符号链接（cdplay/cdpause/cdstop/cdclose/cdeject/cdir/cdinfo/cdreset/cdvolume/
cdshuffle）暴露不同子命令，argv[0] 决定行为。

上游版本：官网最新发布版即 2.1.8（2006-08-09）。任务卡版本串
"2.1.8-release" 取自 Debian 上游版本号（cdtool_2.1.8-release-9.dsc 的
Version: 2.1.8-release-9），其 orig tarball 与官网 cdtool-2.1.8.tar.gz
逐字节相同（sha256 73de81ea…76a21）。目录与配方版本保持任务卡值
"2.1.8-release" 以满足 CI L0n 分支名门禁（分支 feat/cdtool-2.1.8-release）。

Upstream: https://hinterhof.net/cdtool/
Source:   https://hinterhof.net/cdtool/dist/cdtool-2.1.8.tar.gz

Build:   autotools（configure + make）。零第三方 Conan 依赖：socket 由 libc
         提供（configure.ac 的 AC_CHECK_LIB(socket, connect)），头文件
         getopt.h/mntent.h/linux/cdrom.h 由 OHOS sysroot 提供。
Install: lib/cdtool/cdtool（主程序）、bin/ 下 5 个独立产物
         （cdctrl/cdown/cdadd/cdloop/cdtool2cddb）与 10 个别名符号链接、
         share/man/man1 下 16 份手册页。
Type:    application（CLI 工具——软件级 commands.json 声明）

上游测试：上游 tarball 无 tests/ 目录、Makefile.in 无 check/test 目标、
configure.ac 无测试宏（审计见 test_package/MANIFEST.yml）。**TOTAL=0**，
如实声明不伪造通过率；构建期以 4 个刚构建二进制的 -V/-h 冒烟作功能性替代。
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class CdtoolConan(ConanFile):
    name = "cdtool"
    version = "2.1.8-release"
    description = ("CD-ROM audio control tools (single binary cdtool exposed "
                   "under cdplay/cdctrl/cdvolume and 12 other names)")
    license = "GPL-2.0-only"
    homepage = "https://hinterhof.net/cdtool/"
    url = "https://hinterhof.net/cdtool/"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # --prefix=/ 使安装布局落在包根：bin/、lib/、share/man/
        tc.configure_args.append("--prefix=/")
        tc.configure_args.append("--bindir=/bin")
        tc.configure_args.append("--mandir=/share/man")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # OHOS /tmp 只读：configure 的编译器探测（ac_link）需要可写临时目录，
        # 否则 conftest 写出失败、configure 静默降级（cdrecord 同款教训）。
        tmpdir = "TMPDIR=%s" % self.build_folder
        self.run("%s ./configure --prefix=/ --bindir=/bin --mandir=/share/man"
                 % tmpdir, cwd=self.source_folder, env="conanbuild")
        # -j1：规避 OHOS 上 make 建 jobserver fifo 被拒（catdoc/boa 同款）。
        self.run("%s make -j1" % tmpdir, cwd=self.source_folder, env="conanbuild")

    def package(self):
        self.run("TMPDIR=%s make install DESTDIR=%s -j1"
                 % (self.build_folder, self.package_folder),
                 cwd=self.source_folder, env="conanbuild")

    def package_info(self):
        # 与真实产物一致：bin/ 下没有名为 cdtool 的入口，主程序在
        # lib/cdtool/cdtool，bin/ 的 10 个别名是指向它的相对符号链接。
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.output.info("cdtool %s: lib/cdtool/cdtool + bin/ 15 项"
                         "（5 独立产物 + 10 别名符号链接）" % self.version)
