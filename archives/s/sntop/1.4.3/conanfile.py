#!/usr/bin/env python3
"""sntop 1.4.3 —— ncurses 终端网络主机连通性监视器（CLI/curses 应用）。

构建要点（一手实测，详见同目录 notes.md）：
  * 上游 configure 是 autoconf 2.13 产物（无 configure.ac），只认环境变量、
    把命令行 ``VAR=value`` 判成 host 三元组并 error 退出 —— 依赖路径一律走 env。
  * 上游 Makefile.in 的 CFLAGS 行完全不引用 ``@CFLAGS@``/``@LDFLAGS@``，
    configure 探到的编译旗标进不了真正的编译命令：
      - 头文件路径经上游本就使用的 ``-I$(INCLUDE)`` 钩子注入（make 变量 INCLUDE）；
      - 库搜索路径随 ``LIBS`` 进 ``@LIBS@``（该占位符是存在的）。
  * 上游 install 规则不支持 DESTDIR，且 ``$(ETCDIR)``/``$(INSTDIR)`` 不存在时
    直接 ``false``，故先创建目录、装到私有 pkgroot，再由 package() 搬进包目录。
  * ``CONF_SFILE`` 由 make 变量 ``SNTOPRC`` 在编译期烧进二进制，指向上游文档
    约定的用户级 prefix（DEFAULT_PREFIX 可覆盖，缺省 ~/usr/local），
    不写包缓存路径（缓存目录随 package id 变化，烧进二进制即失效）。
"""
import os

from conan import ConanFile
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (apply_conandata_patches, copy,
                              export_conandata_patches, get)


class SntopConan(ConanFile):
    name = "sntop"
    version = "1.4.3"
    description = ("sntop (simple network top) —— 基于 ncurses 的终端网络主机"
                   "连通性监视器：按配置清单轮询各主机的 UP/DOWN 状态，以 top "
                   "式界面显示，支持守护模式、报警脚本与 HTML 报表")
    license = "GPL-2.0-only"
    homepage = "https://sntop.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("network", "monitor", "ncurses", "cli", "harmonyos-pc")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # ncurses 归档产物为宽字符静态库 libncursesw.a（--without-shared +
        # --enable-widec），与本包同源的 curses 工具在此仓库统一取 6.5。
        self.requires("ncurses/6.5")

    def layout(self):
        # 上游 configure 用 ac_unique_file=sntop.c 在同目录定位源码，
        # install 规则又以相对路径 cp sntop —— 按上游 INSTALL 的用法原地构建。
        self.folders.source = "."
        self.folders.build = "."
        self.folders.generators = os.path.join(".", "conan")

    def _pkgroot(self):
        return os.path.join(self.build_folder, "pkgroot")

    def _ncurses_dir(self, part):
        return os.path.join(self.dependencies["ncurses"].package_folder, part)

    def _runtime_conf(self):
        prefix = os.environ.get("DEFAULT_PREFIX") or \
            os.path.join(os.path.expanduser("~"), "usr", "local")
        return os.path.join(prefix, "etc", "sntoprc")

    def _make_vars(self):
        # 两条 make 调用必须传同一组变量，避免 install 触发重编译后
        # 烧进二进制的 CONF_SFILE 变成暂存路径。
        return ('INCLUDE="{}" SNTOPRC="{}"'.format(
            self._ncurses_dir("include"), self._runtime_conf()))

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        # 取 profile 的 [buildenv]（PATH / CONFIG_SHELL / SHELL）与
        # tools.build:compiler_executables，避免 build() 依赖裸 shell 变量（R33）。
        VirtualBuildEnv(self).generate()
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = executables.get("c") or "clang"
        inc = self._ncurses_dir("include")
        lib = self._ncurses_dir("lib")
        env = Environment()
        env.define("CC", cc)
        env.define("CPPFLAGS", "-I{}".format(inc))
        env.define("LDFLAGS", "-L{}".format(lib))
        # 归档的 ncurses 不提供 libncurses.a，上游 AC_CHECK_LIB(ncurses, printw)
        # 的 -lncurses 探测必然 "no"（该结果不被任何源码读取，是良性假阴），
        # 真正链接用的 -lncursesw 由 LIBS 提供。
        env.define("LIBS", "-L{} -lncursesw".format(lib))
        env.vars(self, scope="build").save_script("conanbuild_sntop")

    def build(self):
        pkgroot = self._pkgroot()
        self.run('bash ./configure --prefix="{}" --mandir="{}/share/man"'.format(
            pkgroot, pkgroot), env="conanbuild")
        self.run("make {}".format(self._make_vars()), env="conanbuild")
        for d in ("bin", "etc", os.path.join("share", "man", "man1")):
            os.makedirs(os.path.join(pkgroot, d), exist_ok=True)
        self.run("make {} install".format(self._make_vars()), env="conanbuild")

    def package(self):
        pkgroot = self._pkgroot()
        copy(self, "*", src=os.path.join(pkgroot, "bin"),
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "*", src=os.path.join(pkgroot, "etc"),
             dst=os.path.join(self.package_folder, "etc"))
        copy(self, "*", src=os.path.join(pkgroot, "share"),
             dst=os.path.join(self.package_folder, "share"))
        copy(self, "COPYING", src=self.build_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # application 包：只对外暴露可执行文件，不导出库/头。
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["etc", "share"]
