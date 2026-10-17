#!/usr/bin/env python3
"""Conan recipe — baka 2.0.4（Baka MPlayer，Qt5 + libmpv 多媒体播放器，构建系统 qmake）。

Status: built（路径 A 恢复——上游依赖 qt5-qtx11extras/libass/libmpv 已发布，
依赖链闭合后重新编译验证）

依赖链（W0 依赖发布检查确认均已发布）：
- QT += core gui network svg      → qt5-qtbase/5.15.2 + qt5-qtsvg/5.15.2
- QT += x11extras                 → qt5-qtx11extras/5.15.2
- PKGCONFIG += x11                → libx11/6.4.0（x11.pc）
- PKGCONFIG += mpv                → libmpv/0.41.0（mpv.pc，硬依赖）
"""
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, get, export_conandata_patches
from conan.tools.layout import basic_layout


class BakaConan(ConanFile):
    name = "baka"
    version = "2.0.4"
    description = "Baka MPlayer — a free and open source, cross-platform, libmpv based multimedia player (Qt5)"
    license = "GPL-2.0"
    homepage = "https://github.com/u8sand/Baka-MPlayer"
    url = "https://github.com/u8sand/Baka-MPlayer"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # qt5-qtbase/5.15.2 为 -no-widgets 构建（无 Qt5Widgets），baka 的
        # Baka-MPlayer.pro 声明 QT += widgets，须依赖启用 Widgets 的 5.15.2.2。
        # qt5-qtsvg/5.15.2 的 recipe 声明精确 qt5-qtbase/5.15.2（非范围），
        # 与本配方 5.15.2.2 冲突，故用 override 强制统一到 5.15.2.2
        # （5.15.2.x 补丁版本 API 兼容，qtsvg 二进制无需重建）。
        self.requires("qt5-qtbase/5.15.2.2", override=True)
        self.requires("qt5-qtsvg/5.15.2")
        self.requires("qt5-qtx11extras/5.15.2")
        self.requires("libx11/6.4.0")
        self.requires("libmpv/0.41.0")
        # 依赖图版本冲突：qt5-qtbase 链声明 zlib/1.3.1，ffmpeg/7.1.5 链声明
        # zlib/1.3.1.1，统一 override 到 1.3.1.1（1.3.1 的补丁版本，兼容）
        self.requires("zlib/1.3.1.1", override=True)
        # 依赖图版本冲突：dbus 链声明精确 expat/2.8.2，fontconfig/2.18.1.1
        # 声明精确 expat/2.8.2.1（2.8.2 的 .so 无 SONAME，会污染 DT_NEEDED），
        # 统一 override 到 2.8.2.1（2.8.2 的补丁版本，API 兼容）
        self.requires("expat/2.8.2.1", override=True)

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: settings.os 判断必须 in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"baka only supports Linux and OHOS, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def _setup_qmake_modules(self, build_env):
        """qmake 通过 QMAKEMODULES 搜索外部 Qt 模块的 .pri（qt_lib_svg.pri 等）。

        qt5-qtsvg/qt5-qtx11extras 包内 mkspecs/modules 的 .pri 文件记录的是
        **构建时**的绝对路径（构建目录已随 conan 清理消失），qmake 直接引用
        会报 Unknown module(s)。这里复制到本包 build 目录并把路径改写为各
        依赖包的 package 目录，再通过 QMAKEMODULES 暴露给 qmake。
        """
        modules_root = os.path.join(self.build_folder, "qmake-modules")
        modules_dir = os.path.join(modules_root, "modules")
        modules_inst_dir = os.path.join(modules_root, "modules-inst")
        os.makedirs(modules_dir, exist_ok=True)
        os.makedirs(modules_inst_dir, exist_ok=True)
        for dep_name in ("qt5-qtsvg", "qt5-qtx11extras"):
            dep = self.dependencies[dep_name]
            if dep.package_folder is None:
                continue
            pkg_root = dep.package_folder
            for sub, target in (
                ("mkspecs/modules", modules_dir),
                ("mkspecs/modules-inst", modules_inst_dir),
            ):
                src = os.path.join(pkg_root, sub)
                if not os.path.isdir(src):
                    continue
                for pri in os.listdir(src):
                    if not pri.endswith(".pri"):
                        continue
                    shutil.copy2(
                        os.path.join(src, pri), os.path.join(target, pri)
                    )
            # 改写复制后的 .pri：构建目录绝对路径 → 本依赖 package 目录
            for pri in os.listdir(modules_dir):
                if not pri.endswith(".pri"):
                    continue
                path = os.path.join(modules_dir, pri)
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                # 构建目录形如 .../.conan2/p/b/qt5-qXXXX/b（qtsvg）或
                # .../.cache/conan2/p/b/qt5-qXXXX/b（qtx11extras），统一
                # 改写为依赖包的 package 目录（pkg_root 下自带 mkspecs/
                # modules-inst，include 引用随之解析）
                fixed = re.sub(
                    r"(/[^\s]*?conan2/p/b/[^/\s]+/b)",
                    pkg_root,
                    content,
                )
                if fixed != content:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(fixed)
        build_env.define("QMAKEMODULES", modules_dir)

    def build(self):
        # conan 2.29 无 conan.tools.qmake 模块（只有 cmake/meson），
        # 参照 qt5-qtx11extras 先例用 self.run 直接调用 qmake + make
        build_env = Environment()
        qtbase = self.dependencies["qt5-qtbase"]
        qmake_path = os.path.join(qtbase.package_folder, "bin", "qmake")
        if not os.path.exists(qmake_path):
            raise ConanInvalidConfiguration(
                f"qt5-qtbase 包内未找到 qmake: {qmake_path}"
            )
        # PKG_CONFIG_PATH 由全部依赖的 pkgconfig 目录组成（lib/pkgconfig 与
        # share/pkgconfig 两种布局；x11.pc 的 Requires 链需 xorgproto/libxcb/
        # libxau/libxdmcp 的 .pc 文件，libmpv 提供 mpv.pc）
        pkg_paths = []
        for dep in self.dependencies.values():
            if dep.package_folder is None:
                # test/build 上下文依赖（如 check/0.15.2）在 build() 阶段
                # 无 package_folder，跳过
                continue
            for rel in ("lib", "lib/pkgconfig", "share/pkgconfig"):
                pc = os.path.join(dep.package_folder, rel)
                if os.path.isdir(pc) and pc.endswith("pkgconfig"):
                    pkg_paths.append(pc)
        existing_pkg = os.environ.get("PKG_CONFIG_PATH")
        if existing_pkg:
            pkg_paths.append(existing_pkg)
        build_env.define("PKG_CONFIG_PATH", ":".join(pkg_paths))
        # 编译器环境（clang 工具链，与 CI profile 一致）
        build_env.define("CC", "/data/service/hnp/bin/clang")
        build_env.define("CXX", "/data/service/hnp/bin/clang++")
        # qmake 需通过 QMAKEMODULES 发现 qtsvg/qtx11extras 模块（模块 .pri
        # 记录的是已消失的构建目录路径，这里复制改写后指向 package 目录）
        self._setup_qmake_modules(build_env)
        # qtx11extras 公开头 qx11info_x11.h 直接 include <xcb/xcb.h>，
        # baka 源码也经 QtX11Extras 间接引用 xcb 头文件，须补充 libxcb
        # include 路径（参照 qt5-qtx11extras recipe 的 CPATH 先例）。
        # x11.pc 的 prefix 固定为 /（libx11 包内 .pc 未改写 prefix），
        # pkg-config 提供的 include 路径 -I/include 无效，libx11 的头文件
        # 同样须经 CPATH 显式补充（baka 源码 include <X11/Xlib.h>）。
        # 注意：CPATH 是冒号分隔的路径列表，Environment().append 会以空格
        # 拼接导致整个路径失效，必须用 define 一次性写入。
        cpath_dirs = []
        for dep_name in ("libxcb", "libx11", "libmpv"):
            dep = self.dependencies[dep_name]
            if dep.package_folder:
                cpath_dirs.append(
                    os.path.join(dep.package_folder, "include")
                )
        if cpath_dirs:
            build_env.define("CPATH", ":".join(cpath_dirs))
        # 链接期：x11.pc / mpv.pc 的 prefix 固定为 /（libdir=/lib），
        # qmake 从 pkg-config 拿到的 -L/lib 无效，链接 -lX11/-lmpv 找不到
        # 库。用 LIBRARY_PATH（clang 识别）显式补充各依赖 lib 目录。
        library_path_dirs = []
        for dep_name in ("libx11", "libmpv", "libxcb", "zlib"):
            dep = self.dependencies[dep_name]
            if dep.package_folder:
                library_path_dirs.append(
                    os.path.join(dep.package_folder, "lib")
                )
        if library_path_dirs:
            build_env.define("LIBRARY_PATH", ":".join(library_path_dirs))
        with build_env.vars(self).apply():
            jobs = 2  # make -j 在本环境报 jobserver mkfifo 错误，用 -j2
            # 参照 qt5-qtx11extras 先例：在源码目录内运行 qmake + make
            # （in-source build，Makefile 生成于源码目录；qmake 默认 spec
            # 为 linux-g++，须显式 -spec linux-clang 匹配 clang 工具链；
            # QMAKE_STRIP="" 防止 strip —— OHOS 加载器拒绝 stripped ELF）
            self.run(
                f'cd "{self.source_folder}" && '
                f'"{qmake_path}" "{os.path.join(self.source_folder, "src", "Baka-MPlayer.pro")}" '
                f"-spec linux-clang"
            )
            self.run(
                f'cd "{self.source_folder}" && make -j{jobs} QMAKE_STRIP=""'
            )

    def package(self):
        # TARGET=baka-mplayer、DESTDIR=build → 可执行文件位于
        # 源码目录 build/ 子目录下
        src_dir = self.source_folder
        exe = os.path.join(src_dir, "build", "baka-mplayer")
        if os.path.isfile(exe):
            copy(self, "baka-mplayer", src=os.path.dirname(exe),
                 dst=os.path.join(self.package_folder, "bin"), keep_path=False)

    def package_info(self):
        # 二进制应用（TEMPLATE=app），无消费方库目标
        self.cpp_info.bindirs = ["bin"]
