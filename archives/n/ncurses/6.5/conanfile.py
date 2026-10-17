#!/usr/bin/env python3
"""Conan recipe — ncurses 6.5（终端界面库，鸿蒙 aarch64 静态编译）.

ncurses 是终端界面库，提供字符屏幕绘制、窗口管理、键盘输入等能力。
构建系统：autotools
平台：OHOS / Linux（configure() 已限制 os 仅支持这两者）
依赖：无第三方依赖（纯 C 库）
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class NCursesConan(ConanFile):
    name = "ncurses"
    version = "6.5"
    description = "ncurses — 终端界面库（字符屏幕绘制、窗口管理）"
    license = "X11"
    homepage = "https://invisible-island.net/ncurses/"
    url = "https://invisible-mirror.net/archives/ncurses/"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
    generators = ["PkgConfigDeps"]

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"ncurses supports Linux and OHOS, not {self.settings.os}"
            )
        # OHOS 必须静态编译：共享库会劫持系统 libncursesw.so.6 导致 zsh 崩溃
        if self.options.shared and str(self.settings.os) == "OHOS":
            raise ConanInvalidConfiguration(
                "OHOS requires static ncurses (shared lib would shadow system libncursesw.so.6)"
            )
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # OHOS 必须静态编译（--without-shared）：共享库会劫持系统
        # libncursesw.so.6 导致 zsh 崩溃（shared=True 在 OHOS 已被 configure()
        # 拒绝）；Linux 上按 shared 选项动态设置。--enable-widec 宽字符支持
        # （readline/bash 依赖 libncursesw）；--enable-overwrite 头文件装顶层
        if self.options.shared:
            tc.configure_args.append("--with-shared")
        else:
            tc.configure_args.append("--without-shared")
        tc.configure_args.extend([
            "--without-debug",
            "--without-ada",
            "--without-manpages",
            "--without-cxx-binding",
            "--enable-widec",
            "--enable-overwrite",
        ])
        tc.generate()

    def build(self):
        # 官方 tarball 已预生成 configure；out-of-source 构建（conan 默认在
        # build-release 下运行 configure），config.status 依赖 umask 022 补丁
        # （OHOS 沙箱 077 下 mkdir 出的 0700 目录不可写）才能创建子目录 Makefile
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

        # 尽可能运行上游测试（make check，构建 test/ 目录程序并运行非交互
        # 测试；native 编译时执行，-j1 避免 mkfifo 沙箱限制）
        if not cross_building(self):
            autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # 宽字符静态库：libncursesw.a / libpanelw.a / libmenuw.a / libformw.a
        self.cpp_info.libs = ["ncursesw", "panelw", "menuw", "formw"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "ncurses")
        self.cpp_info.set_property("cmake_target_name", "ncurses::ncurses")
        self.cpp_info.set_property("pkg_config_name", "ncursesw")
