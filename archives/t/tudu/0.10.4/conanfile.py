#!/usr/bin/env python3
"""Conan recipe for tudu 0.10.4 — 终端分层 Todo 列表管理器（ncurses TUI）。

Build system: acr 生成的 ./configure + make（非 GNU autotools；acr 的 configure
              不识别 --host/--build 等标准交叉参数，故采用手动注入编译环境的方式）。
依赖：ncurses/6.5（OHOS 静态链接 libncursesw.a；R26 系统同名库禁止动态）。
补丁：patches/configure-clang-implicit-int.patch（acr configure 的编译探针使用
      隐式 int main()，clang 15 视作硬错误；改为显式 int main()，属通用 clang 适配，
      不含 __OHOS__ 宏，PF5 合规）。
上游测试：无自动化测试套件（Makefile 仅 all/install/uninstall/dist/clean/mrproper，
          无 check/test 目标，源码树无 test/ 目录）。消费者可行性由 test_package 覆盖。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    copy,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class TuduConan(ConanFile):
    name = "tudu"
    version = "0.10.4"
    description = "Terminal hierarchical todo list manager (ncurses TUI)"
    license = "GPL-3.0-or-later"
    homepage = "https://savannah.nongnu.org/projects/tudu"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32：只允许 Linux / OHOS，不能用 == "Linux" 排除 OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("tudu only supports Linux and OHOS")

    def requirements(self):
        # OHOS 必须静态 ncurses（ncurses OHOS 配方拒绝 shared）
        self.requires("ncurses/6.5", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self)
        # acr configure 不支持 out-of-source build，强制 in-source
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # 本机与目标同为 OHOS aarch64（非交叉），AutotoolsToolchain 不会注入
        # --host 等 acr 不识别的参数，可安全使用；它负责生成 conanbuild.conf
        # 并据 conf 设置 CC/CXX 为 OHOS clang。
        tc = AutotoolsToolchain(self)
        dep = self.dependencies["ncurses"]
        inc_flags = [f"-I{i}" for i in dep.cpp_info.includedirs]
        lib_flags = [f"-L{l}" for l in dep.cpp_info.libdirs]
        # 关键：acr 的 WIDEC 探针只用 ${CXXFLAGS}（不含 ${CPPFLAGS}），
        # 必须把 ncurses 头文件路径同时放到 CXXFLAGS/CFLAGS，否则找不到 curses.h。
        # 注意：必须扩展 extra_* 可变属性，computed 的 cxxflags/cflags 每次重算会丢失。
        tc.extra_cxxflags.extend(inc_flags)
        tc.extra_cflags.extend(inc_flags)
        tc.extra_ldflags.extend(lib_flags)
        # CHKLIB 链接 ncursesw（configure 优先 -lncursesw）
        tc.extra_ldflags.append("-lncursesw")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # 直接调用 ./configure；不传 --host（acr 不识别）
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        # 二进制落在 src/tudu；许可证为 COPYING（GPL 全文）
        copy(self, "tudu",
             src=os.path.join(self.build_folder, "src"),
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "COPYING*", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
