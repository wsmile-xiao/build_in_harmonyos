#!/usr/bin/env python3
"""Conan recipe — x3270 4.4ga6 (suite3270)

suite3270: x3270/c3270/s3270/b3270/tcl3270/pr3287 系列 IBM 3270 终端模拟器。
鸿蒙 PC (aarch64, OHOS) 适配：
- 无 X11 环境，禁用 GUI 组件 x3270/wc3270 等，仅构建命令行组件
  (s3270/b3270/c3270/pr3287/x3270if/playback/mitm/lib)。
- 无 tcl 运行时，禁用 tcl3270。
- config.guess/config.sub 补丁识别 aarch64-unknown-linux-ohos (E007)。
- configure 脚本 umask 077→022 修复 HMDFS 权限问题 (E011)。
- x3270if.c 补 <termios.h> include 修复 OHOS 下 termios 未定义。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class X3270Conan(ConanFile):
    name = "x3270"
    version = "4.4ga6"
    description = "suite3270: IBM 3270 terminal emulator suite (s3270/b3270/c3270/pr3287)"
    license = "MIT"
    homepage = "https://x3270.miraheze.org/"
    url = "https://github.com/pmattes/x3270"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")
        if self.settings.arch not in ("armv8", "aarch64"):
            raise ConanInvalidConfiguration("x3270 builds require aarch64 (armv8)")

    def requirements(self):
        self.requires("ncurses/6.6")        # c3270 终端渲染（与 readline/8.3 依赖一致）
        self.requires("readline/8.3")       # c3270 命令行编辑
        self.requires("expat/2.8.2")        # b3270 XML 解析
        self.requires("openssl/3.5.6")      # TLS 支持（lib/configure 检测 openssl/ssl.h，缺失则 TLS 禁用）

    def layout(self):
        # x3270 顶层 Makefile 依赖源码树内相对路径（lib3270_files.mk 位于
        # Common/，obj/ 目录由 configure 在源码树内生成），不支持 out-of-source
        # 构建（CI 实测 build-release 目录下 make 报 lib3270_files.mk 缺失）。
        # 因此强制 in-tree 构建：build 目录即源码目录。
        self.folders.build = "."
        self.folders.generators = os.path.join(".", "conan")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 鸿蒙无 X11/tcl：禁用 GUI 与 tcl 组件，构建命令行组件
        tc.configure_args.extend([
            "--disable-x3270",
            "--disable-tcl3270",
            "--disable-wc3270",
            "--disable-ws3270",
            "--disable-wb3270",
            "--disable-wpr3287",
            "--disable-wx3270if",
            "--disable-wplayback",
            "--disable-wmitm",
            "--disable-windows-lib",
        ])
        # 注入依赖 include/lib 路径：AutotoolsToolchain 不会自动注入
        # 依赖包 cpp_info（CI #21036 教训：无 extra_cppflags 属性，用
        # extra_cflags；configure 头文件检测与链接测试均继承这些标志）
        for dep in ("ncurses", "readline", "expat", "openssl"):
            pkg = self.dependencies[dep].package_folder
            tc.extra_cflags.append(f"-I{os.path.join(pkg, 'include')}")
            tc.extra_ldflags.append(f"-L{os.path.join(pkg, 'lib')}")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # 命令行二进制放入 bin/（构建 triple 与 validate() 一致：OHOS aarch64）
        obj_dir = os.path.join(self.source_folder, "obj", "aarch64-unknown-linux-ohos")
        for b in ["s3270", "b3270", "c3270", "pr3287", "x3270if", "playback", "mitm"]:
            copy(self, b, src=os.path.join(obj_dir, b),
                 dst=os.path.join(self.package_folder, "bin"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
