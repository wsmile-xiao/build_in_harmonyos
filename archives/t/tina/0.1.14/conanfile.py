#!/usr/bin/env python3
"""Conan recipe — tina 0.1.14（个人事务管理器，鸿蒙 aarch64 交叉编译）.

tina 是 curses 界面的个人事务管理器：分类管理短文本条目。
构建系统：autotools（configure.ac + Makefile.am，AC_CHECK_LIB(curses, initscr)）
平台：OHOS / Linux
依赖：ncurses（curses initscr）
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.env import Environment
from conan.tools.files import get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class TinaConan(ConanFile):
    name = "tina"
    version = "0.1.14"
    description = "tina — 个人事务管理器（curses 界面）"
    license = "GPL-2.0-or-later"
    homepage = "https://devel.ringlet.net/misc/tina/"
    url = "https://gitlab.com/tina-mgr/tina-mgr"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}
    generators = ["PkgConfigDeps"]
    requires = ("ncurses/6.5",)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"tina supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        import os
        get(self, **self.conan_data["sources"], strip_root=True)
        # OHOS 沙箱：config.status 临时目录 mkdir 077 不可写 → umask 022
        cfg = os.path.join(self.source_folder, "configure")
        with open(cfg, "r") as f:
            text = f.read()
        text = text.replace("umask 077", "umask 022")
        with open(cfg, "w") as f:
            f.write(text)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--without-shared")
        tc.generate()
        # AC_CHECK_LIB(curses, initscr)：ncurses 库名是 ncursesw，
        # configure 探测 -lcurses → 需在 lib 目录创建 libcurses.a 符号链接
        # 并把 include/lib 目录注入 CPPFLAGS/LDFLAGS
        nc = self.dependencies["ncurses"].cpp_info.aggregated_components()
        libdir = nc.libdirs[0]
        incdir = nc.includedirs[0]
        self.output.info(f"ncurses lib={libdir} include={incdir}")
        env = Environment()
        env.append("CPPFLAGS", f"-I{incdir}")
        env.append("LDFLAGS", f"-L{libdir}")
        env.vars(self).save_script("ncurses_flags")

    def build(self):
        # AC_CHECK_LIB(curses, initscr) 探测 -lcurses，
        # 而 ncurses 包提供的是 libncursesw.a → 创建符号链接
        import os
        nc = self.dependencies["ncurses"].cpp_info.aggregated_components()
        libdir = nc.libdirs[0]
        curses_link = os.path.join(libdir, "libcurses.a")
        if not os.path.exists(curses_link):
            os.symlink(os.path.join(libdir, "libncursesw.a"), curses_link)
            self.output.info(f"symlink: {curses_link} -> libncursesw.a")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # 应用包：无库可链接，仅暴露 bin/tina（test_package 按 package_folder/bin/tina 取）
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
