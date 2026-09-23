#!/usr/bin/env python3
"""Conan recipe for zile 2.6.4 — lightweight Emacs clone (Autotools, application).

Build system: Autotools（configure + make，辅助脚本在 build-aux/）。
核心依赖（configure.ac 一次 PKG_CHECK_MODULES 检查）：
  glib-2.0/gobject-2.0/gio-2.0 + gee-0.8（libgee）→ PkgConfigDeps 提供 .pc；
  curses（AX_WITH_CURSES 探测）→ conan ncurses 包只出 widec（ncursesw），
  显式 CURSES_LIB=-lncursesw 防宏回落 -lcurses。
上游 2.6 系列以 Vala 编写，官方 tarball 自带预生成 .c 与 *_vala.stamp，
AM_PROG_VALAC 缺失仅 WARN，无需 valac。
config.guess 2024-07-27 不识别 uname -s=HarmonyOS（补丁 0001 加 case）；
config.sub 同版本已原生支持 ohos（实测，免补丁）；configure 的 umask 077
临时目录在 HMDFS 上 Permission denied（E011/E114 同类，补丁 0002 改 022）。
上游测试：make check 跑 src/estr-test（src/Makefile.am TESTS=check_PROGRAMS）。
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class ZileConan(ConanFile):
    name = "zile"
    version = "2.6.4"
    description = "GNU Zile is a lightweight Emacs clone"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/zile/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # 全图 glib 必须单实例：remote glib/2.84.0 仅有 static 变体，而 libgee
    # shared binary 内嵌了另一份 static glib → 消费程序（静态链 glib）与
    # libgee.so（内嵌 glib）各持一份 gobject 类型系统，
    # gtype.c:2556 static_quark_type_flags 断言 SIGABRT（设备实测）。
    # libgee 改用 static 变体使 glib 仅存在一份；CI 经 --build=missing
    # 本地构建 libgee（glib/libffi/pcre2 仍走制品仓现成 binary）。
    default_options = {"libgee/*:shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 裸格式引用（ohpcd 制品仓无 user/channel）。
        # transitive：gee-0.8.pc Requires glib-2.0/gobject-2.0，configure 的
        # PKG_CHECK_MODULES([GLIB], [glib-2.0 gobject-2.0 gio-2.0 gee-0.8])
        # 需要 glib 的头/库与 .pc 全部可见（libgee 配方同款 transitive 处理）。
        # libgee 用 0.20.8（制品仓已发布）：0.20.8.1 为工程修复版（同源码，
        # 仅配方加 Skipped 依赖守卫），制品未上传，引用它 CI 依赖解析必挂。
        self.requires("glib/2.84.0", transitive_headers=True, transitive_libs=True)
        self.requires("libgee/0.20.8", transitive_headers=True, transitive_libs=True)
        self.requires("ncurses/6.5")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # 先生成依赖 .pc（PkgConfigDeps 按各包 pkg_config_name 输出，
        # 含 gee-0.8.pc/ncursesw.pc），再统一注入 PKG_CONFIG_PATH。
        PkgConfigDeps(self).generate()

        tc = AutotoolsToolchain(self)
        env = tc.environment()
        # 遍历全部依赖（含传递依赖）：glib-2.0.pc 的 Requires 链、
        # curses 头/库探测都需要 include/lib 路径注入。
        for dep in self.dependencies.values():
            # 静态内嵌 vendor 依赖（Skipped binaries）无 package_folder，跳过
            if not dep.package_folder:
                continue
            for inc in dep.cpp_info.includedirs:
                tc.extra_cflags.append(f"-I{inc}")
            for libdir in dep.cpp_info.libdirs:
                tc.extra_ldflags.append(f"-L{libdir}")
                tc.extra_ldflags.append(f"-Wl,-rpath,{libdir}")
            for pkg_dir in (os.path.join(dep.package_folder, "lib", "pkgconfig"),
                            os.path.join(dep.package_folder, "share", "pkgconfig")):
                if os.path.isdir(pkg_dir):
                    env.append_path("PKG_CONFIG_PATH", pkg_dir)
            bin_dir = os.path.join(dep.package_folder, "bin")
            if os.path.isdir(bin_dir):
                env.append_path("PATH", bin_dir)
            for libdir in dep.cpp_info.libdirs:
                env.append_path("LD_LIBRARY_PATH", libdir)
        # 依赖包自带的 .pc 有 Requires 链缺口时由 PkgConfigDeps 生成的
        # .pc 兜底（generators_folder 最后加入搜索路径）。
        env.append_path("PKG_CONFIG_PATH", self.generators_folder)
        # AX_WITH_CURSES：conan ncurses 只出 widec，显式指库防回落 -lcurses。
        env.define("CURSES_LIB", "-lncursesw")
        # help2man 缺失：doc/zile.1.in 规则依赖新编译的 src/zile 二进制，
        # 每次构建必触发 man 页重建 → help2man: not found（Error 127）。
        # tarball 自带预生成 doc/zile.1.in，用 autoconf cache 变量把
        # HELP2MAN 顶替为 /bin/true（rc=0 不产出），保留发布 man 页。
        env.define("ac_cv_path_HELP2MAN", "/bin/true")
        tc.generate(env=env)

    def build(self):
        apply_conandata_patches(self)
        # E490：部分适配路径拷贝源码时丢失执行位，autotools 辅助脚本
        # 不可执行会让 configure 直接 "Permission denied"。
        for _aux in ("configure",
                     "build-aux/config.guess", "build-aux/config.sub",
                     "build-aux/install-sh", "build-aux/missing",
                     "build-aux/compile", "build-aux/test-driver"):
            _p = os.path.join(self.source_folder, _aux)
            if os.path.exists(_p):
                os.chmod(_p, os.stat(_p).st_mode | 0o111)
        # CI 从 ohpcd 下载的依赖包自带 .la 文件，其中被 conan relocatable
        # 打包改坏的绝对路径导致 libtool 链接时报
        # "error: '//lib/xxx.la' is not a valid libtool archive"
        #（libgee 配方同款清理）。
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            lib_dir = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(lib_dir):
                for _la in os.listdir(lib_dir):
                    if _la.endswith(".la"):
                        os.remove(os.path.join(lib_dir, _la))
                        self.output.info(f"removed broken libtool archive: {dep.ref}/{_la}")
        autotools = Autotools(self)
        autotools.configure()
        # VALAC=:：tarball 自带预生成 .c 与 *_vala.stamp，但 zile 的 stamp
        # 规则无条件 touch src/dummy.vala 并重跑 valac（设备无 valac，
        # AM_PROG_VALAC 缺失仅 WARN、Makefile 保留默认 valac）→ Error 127。
        # 用 POSIX no-op ":" 替位使 stamp 规则成功、直接编译发布 .c。
        autotools.make(args=["-j1", "VALAC=:"])
        # 上游官方测试：make check（automake TESTS = src/estr-test +
        # LISP_TESTS/LISP_TESTS_ZILE_ONLY 共 176 项）。zile 为 curses
        # 全屏程序，make check 无 TTY 且 OHOS 无系统 terminfo 数据库，
        # ncurses 初始化报 "Error opening terminal" → lisp 用例全部
        # exit 1；conan ncurses 包自带 terminfo，TERMINFO 指向之并
        # 固定 TERM=xterm（设备实测可正常进入编辑器执行 lisp 并存盘）。
        _terminfo = ""
        for dep in self.dependencies.values():
            if dep.ref.name == "ncurses" and dep.package_folder:
                _t = os.path.join(dep.package_folder, "share", "terminfo")
                if os.path.isdir(_t):
                    _terminfo = _t
                    break
        _pre = "TERM=xterm "
        if _terminfo:
            _pre += f"TERMINFO={_terminfo} "
        self.run(f"{_pre}make check -j1 VALAC=:", env="conanbuild")

    def package(self):
        # install 阶段 install-recursive 仍会触发 vala stamp 规则重跑
        # valac（同 build()），VALAC=: 必须同样传入。
        Autotools(self).install(args=["VALAC=:"])

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
