#!/usr/bin/env python3
"""Conan recipe — wmget 0.6.1（Window Maker 后台下载管理器 DockApp，直编）。

wmget 是 Window Maker 的后台下载管理器：`wmget dock` 为 X11 DockApp 服务器
（下载队列经 SysV shm + fork 共享），客户端子命令（request/list/cancel/
--help/--version）经 UNIX 套接字与服务器通信，不触碰 X。

构建说明：上游 tarball 只带 configure.ac/Makefile.am（无预生成 configure），
真实构建仅需将 13 个 .c 编译链接（-lX11 -lXext -lXpm -lcurl），本配方直编：
- R33：编译器从 tools.build:compiler_executables conf 取（profile 注入），
  conanbuild 环境由 AutotoolsToolchain 生成（含 OHOS triplet/sysroot 标志），
  并以「CFLAGS 为空即退出 9」守卫拒绝静默失败。
- R49：依赖注入仅指向各依赖包私有 package_folder（include/lib）。

平台事实（真机探针，见 notes.md「平台事实」节）：OHOS PC 内核对 SysV IPC
shmget/shmat 运行期 SIGSYS(31) 拦截（编译链接不受影响）；dock 服务器模式
需 X 显示，本包无头验证覆盖 CLI 契约（--version/--help rc=0）。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class WmgetConan(ConanFile):
    name = "wmget"
    version = "0.6.1"
    description = "wmget 0.6.1（Window Maker 后台下载管理器 DockApp，libcurl + X11）"
    license = "MIT"
    homepage = "https://www.dockapps.net/wmget"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libx11/6.4.0")       # Xlib（dockapp/da_x.c、server.c）
        self.requires("libxext/6.4.0.1")    # XShape（X11/extensions/shape.h）
        self.requires("libxpm/3.5.17")      # XPM 图标（X11/xpm.h）
        self.requires("curl/8.15.0.1")      # 下载引擎（retrieve.c）

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"wmget supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # 生成 conanbuild 环境（CC/CFLAGS/LDFLAGS，含 OHOS triplet 与 sysroot）
        tc = AutotoolsToolchain(self)
        tc.generate()

    def _dep_flags(self):
        """聚合依赖 include/lib 路径与库名（仅指向依赖包私有 folder，R49）。

        依赖图中可能混入无包产物的节点（tool_requires/构建辅助件，
        package_folder=None），跳过并向构建日志告警，便于核对缺漏。
        """
        incs, ldirs, libs = [], [], []
        for dep in self.dependencies.values():
            if not dep.package_folder:
                self.output.warning(
                    f"dep {getattr(dep, 'ref', '?')} has no package_folder, skipped"
                )
                continue
            for inc in dep.cpp_info.includedirs:
                incs.append(f"-I{os.path.join(dep.package_folder, inc)}")
            for libdir in dep.cpp_info.libdirs:
                ldirs.append(f"-L{os.path.join(dep.package_folder, libdir)}")
            for lib in dep.cpp_info.libs or []:
                libs.append(f"-l{lib}")
        return " ".join(incs), " ".join(ldirs), " ".join(libs)

    def build(self):
        apply_conandata_patches(self)

        # R33：编译器从 conf 取（ohos-aarch64 profile 注入 clang 路径）
        comp = self.conf.get(
            "tools.build:compiler_executables", check_type=dict, default={}
        )
        cc = comp.get("c", "clang")

        # 上游 Makefile.am 的 wmget_SOURCES 中的全部 C 源（config.def/.xpm 为
        # #include 附属件，不单独编译）
        srcs = ("cancel.c configure.c iq.c list.c messages.c request.c "
                "retrieve.c server.c usage.c wmget.c "
                "dockapp/da_mouse.c dockapp/da_run.c dockapp/da_x.c")
        incs, ldirs, libs = self._dep_flags()

        # automake DEFS 等价物：wmget.h 用 PACKAGE_VERSION 拼版本 banner
        # （AC_INIT([wmget],[0.6.1]) 的产物；绕过 autotools 后须显式提供，
        # 否则残留标识符撞断字符串拼接 → 多处 error: expected ')'）
        pkgver = "-DPACKAGE_VERSION='\"0.6.1\"'"

        # 直编 13 个源文件；conanbuild 环境提供 OHOS CFLAGS/LDFLAGS。
        # 守卫：CFLAGS 为空 = 工具链环境未生成，立即失败（拒绝静默编译）。
        self.run(
            f'test -n "$CFLAGS" || {{ echo "conanbuild CFLAGS is empty"; exit 9; }}; '
            f'"{cc}" $CFLAGS -O2 -Wall {pkgver} -o wmget {srcs} {incs} '
            f'$LDFLAGS {ldirs} {libs}',
            env="conanbuild",
            cwd=self.source_folder,
        )

    def package(self):
        src = self.source_folder
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        shutil.copy2(os.path.join(src, "wmget"), os.path.join(bin_dir, "wmget"))

        # man 页（上游 dist_man_MANS；wmget.1.in 仅 @VERSION@ 一处替换）
        man_dir = os.path.join(self.package_folder, "share", "man", "man1")
        os.makedirs(man_dir, exist_ok=True)
        with open(os.path.join(src, "wmget.1.in"), encoding="utf-8") as fh:
            man = fh.read().replace("@VERSION@", self.version)
        with open(os.path.join(man_dir, "wmget.1"), "w", encoding="utf-8") as fh:
            fh.write(man)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.conf_info.define("user.wmget:bin", "wmget")
