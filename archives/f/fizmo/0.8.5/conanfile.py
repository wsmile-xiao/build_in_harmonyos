#!/usr/bin/env python3
"""Conan recipe — fizmo 0.8.5（Z-Machine 交互小说解释器）.

fizmo 是 Z-Machine 解释器（Fizmo Interprets Z-Machine Opcodes），
可运行 Infocom 及大部分 Z-Machine 交互小说（版本 1-5, 7, 8）。
构建系统：GNU Autotools（configure + make）
平台：OHOS aarch64 / Linux / macOS
依赖：ncurses/6.5（fizmo-ncursesw 前端需要 wide-char ncursesw）
"""

import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain, Autotools


class FizmoConan(ConanFile):
    name = "fizmo"
    version = "0.8.5"
    description = "fizmo — Z-Machine interpreter (Z-Machine interactive fiction)"
    license = "BSD-3-Clause"
    homepage = "https://fizmo.spellbreaker.org/"
    url = "https://github.com/chrender/fizmo"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # fizmo-ncursesw 前端依赖 wide-char ncurses（ncursesw）
        self.requires("ncurses/6.5")
        # fizmo configure 检测 libxml-2.0（pkg-config）+ libxml/tree.h，缺依赖
        # 则报 "Could not find libxml/tree.h"（CI #17356）
        self.requires("libxml2/2.15.3")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def _machine(self, arch):
        # 从 arch setting 推导 GNU 三元组 machine 部分
        return {
            "armv8": "aarch64",
            "armv7": "arm",
            "x86_64": "x86_64",
            "x86": "i686",
        }.get(str(arch), str(arch))

    def generate(self):
        tc = AutotoolsToolchain(self)
        # fizmo 的 config.guess 可能无法识别 HarmonyOS，指定 --build/--host 三元组
        machine = self._machine(self.settings.arch)
        triplet = f"{machine}-unknown-linux-gnu"
        # --disable-x11：fizmo configure 用 --enable-x11 选项（configure 2384 行），
        # 只构建 ncursesw 终端前端，禁用 X11 前端（CI #17368 报 No package 'x11' found）
        # --disable-jpeg：fizmo configure 支持 --disable-jpeg（configure 1495 行），
        # 禁用 JPEG 图像支持（文本 Z-machine 解释器不需要；CI #17480 报
        # Could not find libjpeg.h）
        # --disable-png：fizmo configure 支持 --disable-png（configure 1496 行），
        # 禁用 PNG 图像支持（文本 Z-machine 解释器不需要；CI #17945 报
        # No package 'libpng' found）
        # --disable-sdl：fizmo configure 支持 --disable-sdl（configure 1491 行），
        # 禁用 SDL 前端（只构建 ncursesw 终端前端；CI #21333 报
        # No package 'sdl2' found）
        tc.configure_args.extend(
            [f"--build={triplet}", f"--host={triplet}",
             "--disable-x11", "--disable-jpeg", "--disable-png",
             "--disable-sdl"])
        # fizmo configure 硬编码路径检测 libxml/tree.h（/usr/include/libxml2 等），
        # 需传 --with-libxml2-includedir 指向 libxml2 包 include
        tc.configure_args.append(
            "--with-libxml2-includedir="
            f"{os.path.join(self.dependencies['libxml2'].package_folder, 'include', 'libxml2')}")
        # babel.c 的 #include <libxml/parser.h>（CI #21981 报 libxml/parser.h
        # file not found——编译 -I 是默认 /usr/local/include/libxml2——
        # --with-libxml2-includedir 只影响 configure 检查——编译 -I 需
        # extra_cflags 指向 libxml2 包 include/libxml2【libxml/parser.h 所在】）
        tc.extra_cflags.append(
            f"-I{os.path.join(self.dependencies['libxml2'].package_folder, 'include', 'libxml2')}")
        # fizmo-ncursesw 链接 -lxml2（CI #22091 报 unable to find library
        # -lxml2——链接 -L 未指向 libxml2 包 lib——extra_ldflags 补 -L——
        # 参考 ncurses 的 extra_ldflags 方式）
        tc.extra_ldflags.append(
            f"-L{os.path.join(self.dependencies['libxml2'].package_folder, 'lib')}")
        # ncursesw 前端检查（configure 硬编码路径 /usr/include 等找不到
        # ncurses.h——CI #20171 报 Could not find ncurses.h）——CFLAGS
        # 指向 ncurses 包 include（覆盖 include/ 顶层 + include/ncursesw/
        # 两种布局——multitail 教训）。
        # 注意：AutotoolsToolchain 无 extra_cppflags 属性（CI #20735 实测
        # AttributeError），改用 extra_cflags（configure 的 header 检查
        # 编译测试会用到 CFLAGS 的 -I）
        # ncursesw 前端检查（configure 硬编码路径 /usr/include 等找不到
        # ncurses.h）——CI #21024 实测：extra_cflags 的 -I 传 CFLAGS，但
        # configure 的 ncurses.h 检查（find_file）不读 CFLAGS——需用
        # --with-ncurses-includedir（configure 官方选项——错误消息明确
        # 提示 Try setting the location using --with-ncurses-includedir——
        # 与 --with-libxml2-includedir 一致的模式）
        ncurses = self.dependencies["ncurses"]
        ncurses_inc = os.path.join(ncurses.package_folder, "include")
        ncurses_lib = os.path.join(ncurses.package_folder, "lib")
        tc.configure_args.append(f"--with-ncurses-includedir={ncurses_inc}")
        # ncursesw 库检查（configure 硬编码路径 /usr/lib 等找不到
        # libncursesw——CI #21052 报 Couldn't find libncursesw——
        # --with-ncursesw-libdir 指向 ncurses 包 lib（错误消息明确提示
        # You can set the location manually using --with-ncurses-libdir
        # or --with-ncursesw-libdir）
        tc.configure_args.append(f"--with-ncursesw-libdir={ncurses_lib}")
        # extra_cflags 保留（编译时用——覆盖 include/ 顶层 + include/ncursesw/
        # 两种布局——multitail 教训）
        tc.extra_cflags.append(f"-I{ncurses_inc}")
        tc.extra_cflags.append(f"-I{os.path.join(ncurses_inc, 'ncursesw')}")
        tc.generate()
        # libxml2 的 pkg-config（libxml-2.0）加入 PKG_CONFIG_PATH
        from conan.tools.env import Environment
        env = Environment()
        env.append_path(
            "PKG_CONFIG_PATH",
            os.path.join(self.dependencies["libxml2"].package_folder, "lib", "pkgconfig"),
        )
        env.vars(self).save_script("conanbuild_pkgconfig")

    def build(self):
        autotools = Autotools(self)
        # OHOS 沙箱 umask 077 导致 config.status 临时目录不可写，临时改 022
        old_umask = os.umask(0o022)
        try:
            autotools.configure()
            # -j1 避免 mkfifo 沙箱限制（opensp 先例）
            autotools.make(args=["-j1"])
        finally:
            os.umask(old_umask)

    def package(self):
        # fizmo-ncursesw/fizmo-console 前端二进制在构建产物子目录中
        # （b/fizmo-ncursesw/src/fizmo-ncursesw/ 等——CI 实测：原 copy 源
        # 路径 b/fizmo-ncursesw 不存在【No files in this package】——
        # 递归从 build_folder 找二进制复制到 bin/）
        from conan.tools.files import copy
        # CI #22561 实测：pattern "fizmo-ncursesw" 匹配的是顶层目录
        # （b/fizmo-ncursesw/）——二进制在 src/ 子目录不递归【No files】——
        # 用通配符 "**/fizmo-ncursesw" 递归匹配二进制
        copy(self, "**/fizmo-ncursesw", self.build_folder,
             os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "**/fizmo-console", self.build_folder,
             os.path.join(self.package_folder, "bin"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []