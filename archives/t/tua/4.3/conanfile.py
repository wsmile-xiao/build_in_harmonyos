#!/usr/bin/env python3
"""Conan recipe — tua 4.3 (The UUCP Analyzer)

TUA 读取 Taylor UUCP 的日志与统计文件（Log / Stats），输出按系统、用户、
日期、小时维度的 UUCP 流量报表与费用估算。上游为 1996 年的 ANSI C 程序，
构建系统为 autoconf 2.4 生成的 configure + make。

产物为单个命令行可执行文件 bin/tua → 软件级目录需 commands.json（R38）。

OHOS 适配要点见 4.3/notes.md；补丁见 patches/。
"""
import io
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (get, copy, apply_conandata_patches,
                               export_conandata_patches)
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class TuaConan(ConanFile):
    name = "tua"
    version = "4.3"
    description = ("TUA (The UUCP Analyzer) — analyses Taylor UUCP Log/Stats "
                   "files and prints traffic, user, daily and hourly reports")
    license = "GPL-2.0-or-later"
    homepage = "https://sources.debian.org/src/tua/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # 上游发行包未附 bison 生成的 src/pcdl_gram.c，configure 需要 yacc。
    tool_requires = "bison/3.8.2"

    # E490：HMDFS 下 conan 把源码复制到 build 目录时可能丢失 POSIX 执行位，
    # 导致 configure / mkinstalldirs 以 126 (Permission denied) 失败。
    _AUTOTOOLS_HELPERS = ("configure", "mkinstalldirs", "install.sh")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R1：参数最少化。上游默认启用 Taylor 后端与 glob 别名；NLS 必须关闭，
        # 因为重打包源码不含 intl/（gettext 运行期由 OHOS libc 提供）。
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--disable-nls")
        self._configure_args = list(tc.configure_args)
        tc.generate()

    def _restore_exec_bits(self):
        for root in {self.source_folder, self.build_folder}:
            if not root:
                continue
            for rel in self._AUTOTOOLS_HELPERS:
                path = os.path.join(root, rel)
                if os.path.isfile(path):
                    try:
                        os.chmod(path, os.stat(path).st_mode | 0o111)
                    except OSError:
                        pass

    def _sh_quote(self, arg):
        # 保持 ${prefix} 之类的 shell 占位符原样传给 configure（make 期展开）
        return "'%s'" % arg

    def _run_capture(self, cmd, cwd):
        # 以 StringIO 捕获子进程输出，让 conan 走 subprocess.PIPE 而非继承 fd：
        # OHOS 设备上 clang 经继承 fd 的 fork+exec 链会被静默杀死（无输出、退出 1），
        # PIPE 通道下构建稳定。
        buf = io.StringIO()
        rc = self.run(cmd, cwd=cwd, env="conanbuild",
                      stdout=buf, stderr=buf, ignore_errors=True)
        text = buf.getvalue()
        for line in text.splitlines():
            self.output.info(line)
        if rc != 0:
            raise ConanException("command failed (rc=%d): %s" % (rc, cmd))
        return text

    def build(self):
        apply_conandata_patches(self)
        self._restore_exec_bits()
        # 上游 Makefile.in 由 autoconf 2.4 生成，不支持 out-of-source 构建
        # （规则写死 `$(top_srcdir)/config.status`），因此就地构建在源码目录。
        # OHOS/HMDFS：新写入的脚本文件 execve 可能返回 EACCES（chmod +x 无效），
        # 直接执行 ./configure 会报 126 Permission denied；改由 sh 显式解释执行。
        sf = self.source_folder
        args = " ".join(self._sh_quote(a) for a in self._configure_args)
        self._run_capture('/bin/sh "%s" %s' % (os.path.join(sf, "configure"), args), sf)
        # 串行构建：OHOS 上 make 的 jobserver FIFO 可能不可用
        self._run_capture("make -j1", sf)

    def package(self):
        # 上游 install 目标不使用 $(DESTDIR)，改以 make 变量覆写 prefix 定位到包目录
        sf = self.source_folder
        self._run_capture('make install prefix="%s"' % self.package_folder, sf)
        copy(self, "COPYING", src=sf,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "README", src=sf,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        bin_path = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bin_path):
            self.buildenv_info.append_path("PATH", bin_path)
            self.runenv_info.append_path("PATH", bin_path)
