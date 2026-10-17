#!/usr/bin/env python3
"""Conan recipe — multitail 7.1.5 (日志查看工具，鸿蒙 aarch64).

multitail 是交互式日志查看工具，支持颜色高亮、正则过滤、多文件合并查看等。
构建系统：Makefile
平台：OHOS aarch64 / Linux / macOS
依赖：ncurses
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches
from conan.tools.gnu import PkgConfigDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class MultitailConan(ConanFile):
    name = "multitail"
    version = "7.1.5"
    description = "multitail — 交互式日志查看工具，支持颜色高亮和正则过滤"
    license = "GPL-2.0-only"
    homepage = "https://github.com/folkertvanheusden/multitail"
    url = ""

    settings = "os", "arch", "compiler", "build_type"
    generators = "PkgConfigDeps"
    # 导出 patches/ 目录到 conan 缓存（apply_conandata_patches 在源码目录
    # 找 patch 文件，缺此声明则 patch 未导出报 FileNotFoundError）
    exports_sources = "patches/*"

    def requirements(self):
        self.requires("ncurses/6.5")

    def layout(self):
        basic_layout(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.make_args = []
        tc.generate()
        # multitail 的 GNUmakefile 触发 CMake 配置时未传 ncurses 路径，
        # CMakeLists.txt:69 find_library(panelw) 找不到 libpanelw；设置
        # CMAKE_PREFIX_PATH 指向 ncurses 包（cmake 从环境变量初始化，
        # find_library 会查 $CMAKE_PREFIX_PATH/lib 找到 libpanelw）
        from conan.tools.env import Environment
        env = Environment()
        env.define("CMAKE_PREFIX_PATH", self.dependencies["ncurses"].package_folder)
        # find_package(Curses) 的 find_path 需找 curses.h（include/ncursesw/）
        # 与 find_file(ncurses.h)（include/），CMAKE_PREFIX_PATH 只查
        # $prefix/include 顶层找不到；追加 CMAKE_INCLUDE_PATH（find_path 直接
        # 查条目目录）指向 ncurses 包 include 目录
        ncurses_inc = os.path.join(self.dependencies["ncurses"].package_folder, "include")
        env.append_path("CMAKE_INCLUDE_PATH", ncurses_inc)
        env.append_path("CMAKE_INCLUDE_PATH", os.path.join(ncurses_inc, "ncursesw"))
        # 0003 patch 的 CMakeLists 从 CURSES_INCLUDE_DIR 读 ncurses include，
        # 设置 CURSES_NCURSES_INCLUDE_PATH（FindCurses 用它找 curses.h）。
        # ncurses 包 curses.h 可能在 include/ 顶层或 include/ncursesw/ 子目录
        # （ncursesw 标准布局）——两个路径用分号分隔（cmake 列表，find_path
        # PATHS 展开为两个路径；空格分隔会被视为单个含空格路径——CI #18389
        # 实测仍报缺失）
        env.define(
            "CURSES_INCLUDE_DIR",
            f"{ncurses_inc};{os.path.join(ncurses_inc, 'ncursesw')}",
        )
        env.vars(self).save_script("conanbuild_cmake")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 应用 conandata.yml 注册的补丁（0003-curses-include-env.patch：
        # CMakeLists 从 CURSES_INCLUDE_DIR 读 ncurses include）
        apply_conandata_patches(self)

    def build(self):
        # multitail 无 configure（Makefile 在源码根目录，无 out-of-source 支持），
        # 需在源码目录运行 make（build-release 目录下无 Makefile）；
        # -j1：OHOS 沙箱不支持 mkfifo（jobserver），并行编译失败（opensp 先例）
        # env=["conanbuild", "conanbuild_cmake"]：显式激活 conanbuild_cmake
        # （CURSES_INCLUDE_DIR/CMAKE_PREFIX_PATH——0003 patch 的 CMakeLists
        # 读取 ENV{CURSES_INCLUDE_DIR} 需该环境；仅 conanbuild 不聚合
        # save_script 的独立脚本——CI #18415 实测 CURSES_INCLUDE_PATH 仍缺失）
        self.run("make -j1", cwd=self.source_folder,
                 env=["conanbuild", "conanbuild_cmake"])

    def package(self):
        self.run(f"make install DESTDIR={self.package_folder} PREFIX=/usr",
                 cwd=self.source_folder, env="conanbuild")

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["usr/local/bin"]
