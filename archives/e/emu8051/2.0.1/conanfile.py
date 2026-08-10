#!/usr/bin/env python3
"""Conan recipe — emu8051 2.0.1（8051/8052 微控制器模拟器）.

emu8051 是一个 8051/8052 微控制器模拟器，基于 curses 的终端 UI。
构建系统：Makefile
平台：OHOS aarch64 / Linux / macOS
依赖：ncurses（运行时）、libm（运行时）
"""

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class Emu8051Conan(ConanFile):
    name = "emu8051"
    version = "2.0.1"
    description = "8051/8052 emulator with curses-based UI"
    license = "MIT"
    homepage = "https://github.com/jarikomppa/emu8051"
    url = ""

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("ncurses/6.5")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # emu8051 使用 Makefile 构建。Make 默认 CC=cc 但 OHOS 仅有 clang，
        # 从 settings 获取编译器名称传入 Make。
        compiler = str(self.settings.compiler)
        # 从 ncurses 依赖获取 include 和 lib 路径
        ncurses = self.dependencies["ncurses"]
        cpp_info = ncurses.cpp_info
        # 构建 include 路径和 lib 路径标志
        include_flags = " ".join(f"-I{dir}" for dir in cpp_info.includedirs)
        lib_flags = " ".join(f"-L{dir}" for dir in cpp_info.libdirs)
        # 获取 ncurses 库名（通常是 ncurses 或 ncursesw）
        libs = " ".join(f"-l{lib}" for lib in cpp_info.libs)
        self.run(f"make all CC={compiler} CFLAGS+='{include_flags}' "
                 f"LDLIBS+='{lib_flags} {libs}'")

    def package(self):
        self.run(f"make install DESTDIR={self.package_folder}")

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["usr/bin"]
        self.cpp_info.libdirs = []