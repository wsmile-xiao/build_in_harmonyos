#!/usr/bin/env python3
"""Conan recipe for nettoe — text-based Tic Tac Toe game.

Autotools project (configure + make).
Produces a command-line executable (nettoe).
Requires ncurses (statically linked per R26).

R49 (E524) compliance: dependency injection uses a build_folder private
prefix (`build_folder/prefix`) — CPPFLAGS/LDFLAGS point exclusively at the
private prefix, never at a shared /usr/local (SYS_PREFIX). Each CI worker
build gets an isolated prefix, avoiding cross-contamination between
concurrent builds.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class NettoeConan(ConanFile):
    name = "nettoe"
    version = "1.5.1"
    description = "netToe — text-based Tic Tac Toe game playable over the Internet"
    license = "GPL-2.0"
    homepage = "http://nettoe.sourceforge.net"
    url = "https://github.com/RobertBerger/nettoe"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # R26: ncurses is a system-name library, must be static
        self.requires("ncurses/6.5")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _prefix(self):
        """R49: 依赖注入目标 = build_folder 私有 prefix（不污染共享 /usr/local）。

        CI worker 与本地共享同一台机器的 SYS_PREFIX，注入共享目录会造成
        交叉污染（E524：19 轮 CI 全挂根因）。build_folder 私有 prefix 每轮
        构建独立，天然隔离。
        """
        return os.path.join(self.build_folder, "prefix")

    def _provision_ncurses(self, prefix):
        """将 ncurses 头文件/静态库复制到私有 prefix。

        Conan ncurses/6.5 包只提供 libncursesw.a（wide-char 版），而 nettoe
        configure.ac 检测 `AC_CHECK_LIB([ncurses], [setupterm])` 和
        `AC_CHECK_LIB([tinfo], [setupterm])`，需要 libncurses.a 与 libtinfo.a
        才能通过检测。因此在私有 prefix 中创建这两个副本（实体副本，不用
        软链接——HMDFS 上软链接不可靠）。
        """
        inc_dir = os.path.join(prefix, "include")
        lib_dir = os.path.join(prefix, "lib")
        os.makedirs(inc_dir, exist_ok=True)
        os.makedirs(lib_dir, exist_ok=True)

        ncurses_pkg = self.dependencies["ncurses"].package_folder
        src_inc = os.path.join(ncurses_pkg, "include")
        src_lib = os.path.join(ncurses_pkg, "lib")

        # 头文件：curses.h/ncurses.h/term.h/termcap.h 等
        if os.path.isdir(src_inc):
            for name in os.listdir(src_inc):
                s = os.path.join(src_inc, name)
                d = os.path.join(inc_dir, name)
                if os.path.isfile(s) and not os.path.exists(d):
                    shutil.copy2(s, d)

        # 静态库：libncursesw.a 是唯一可用库
        src_w = os.path.join(src_lib, "libncursesw.a")
        if os.path.isfile(src_w):
            for target in ("libncurses.a", "libtinfo.a", "libncursesw.a"):
                d = os.path.join(lib_dir, target)
                if not os.path.exists(d):
                    shutil.copy2(src_w, d)

    def generate(self):
        tc = AutotoolsToolchain(self)
        prefix = self._prefix()
        self._provision_ncurses(prefix)
        inc_dir = os.path.join(prefix, "include")
        lib_dir = os.path.join(prefix, "lib")
        # R49: CPPFLAGS/LDFLAGS 全指向 build_folder 私有 prefix
        tc.configure_args.append(f"CPPFLAGS=-I{inc_dir}")
        tc.configure_args.append(f"LDFLAGS=-L{lib_dir}")
        # R26: static ncurses (system-name library)
        tc.configure_args.append("--enable-static")
        tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # nettoe is a command-line application, not a library
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        # R38: declare executable in package_info
        self.cpp_info.set_property("cpe:cpe_name", "cpe:2.3:a:nettoe_project:nettoe:1.5.1")
