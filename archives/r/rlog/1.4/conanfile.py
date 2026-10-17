#!/usr/bin/env python3
"""Conan recipe —— rlog 1.4（RLog：C++ 消息日志库）。

上游 tarball 自带 2008 年生成的 configure/Makefile.in，不需要 autoreconf。
适配要点：
  1. 2007 版 config.guess 早于 HarmonyOS：补丁 0001 让它在 HarmonyOS 上直接给出
     aarch64-unknown-linux-gnu，裸 ./configure 才能确定 build type；配方另显式
     给出 --build/--host=aarch64-unknown-linux-gnu（自带 config.sub 接受该三元组，
     无需补丁）。
  2. 补丁 0002 修两处构建环境问题：config.status 的临时目录改用
     `umask 022 && mkdir`（HMDFS 不允许写 mktemp -d 生成的 0700 目录），并把
     clang++ 加入 C++ 编译器候选表（2006 版 autoconf 不认识 clang）。
  3. 补丁 0003 修 docs 安装：install-data-local 的 `../mkinstalldirs`/`html/*`
     相对路径在 VPATH 构建目录不存在，改用 $(top_srcdir)/$(srcdir)。
  4. 上游 configure 默认「只建共享库」（AC_ENABLE_SHARED(yes) /
     AC_ENABLE_STATIC(no)），本配方按 shared 选项显式给出两条开关。
  5. librlog 不是 OHOS 系统同名库（系统与 sysroot 下均无 librlog），按
     非 system 库默认动态（R26 只对系统同名库强制静态）。
  6. 上游 rlog/Makefile.am 用 noinst_PROGRAMS 提供 test/testlog 两个真实
     调用 API 的程序，但没有注册 TESTS（`make check` 为空）；build() 在
     编译后显式运行两者，作为上游功能证据。
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class RlogConan(ConanFile):
    name = "rlog"
    version = "1.4"
    description = "RLog - a flexible message logging library for C++"
    license = "LGPL-2.1-or-later"
    homepage = "https://rlog.sourceforge.net/"
    url = ""

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32：平台判断必须同时接受 Linux 与 OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("rlog is supported only on Linux/OHOS")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS":
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-gnu",
            ])
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # -j1：并行 make 要在 TMPDIR 建 jobserver fifo，HMDFS 上 mkfifo 报
        # "Operation not permitted"（设备实测）；本库 12 个源文件，串行足够
        autotools.make(args=["-j1"])
        # 上游 noinst 程序 test/testlog 真实调用 API，这里显式运行作为上游功能证据。
        # 直接执行 .libs 下的真实二进制并显式给出库路径，不经过 libtool wrapper：
        # VPATH 构建下 wrapper 记录的 relink 命令形如
        #   (cd ; ... -o $progdir/$file test.o ./.libs/librlog.so)
        # （cd 无参数），在 HMDFS 上 getcwd 失效时相对路径解析失败，wrapper 会走
        # relink 分支并以 clang 报错退出（设备实测 exit 1）。
        rlog_build = os.path.join(self.build_folder, "rlog")
        libdir = os.path.join(rlog_build, ".libs")
        for program in ("test", "testlog"):
            self.run(f'LD_LIBRARY_PATH="{libdir}" "{libdir}/{program}"', cwd=rlog_build)

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # libtool 的 *.la 记录构建机路径，不进入包（与归档既有做法一致）
        for la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(la)

    def package_info(self):
        self.cpp_info.libs = ["rlog"]
        self.cpp_info.system_libs = ["pthread"]
