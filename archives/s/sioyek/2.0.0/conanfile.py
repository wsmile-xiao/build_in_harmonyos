#!/usr/bin/env python3
"""Conan recipe — sioyek 2.0.0（ahrm/sioyek，Qt5 + mupdf PDF 阅读器，构建系统 qmake）。

Status: built（本地 conan create + conan-verify 通过，制品未 upload 制品仓）

依赖链（W0 依赖发布检查确认均已发布）：
- QT += core opengl gui widgets network → qt5-qtbase/5.15.2.2（含 Widgets/OpenGL）
  （上游 .pro 的 3dinput/openglextensions 已裁剪，见 patches/0001-ohos-qmake-config.patch）
- mupdf 静态库 bundle（mupdf/mupdf-third/mupdf-pkcs7/mupdf-threads）→ mupdf/1.25.1
- synctex <zlib.h> → zlib/1.3.1（与 qtbase 链同版本，二进制复用制品仓）

构建模式：参照 baka 2.0.4 先例，qmake + make 直调（conan 2.29 无 conan.tools.qmake）。
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class SioyekConan(ConanFile):
    name = "sioyek"
    version = "2.0.0"
    description = "sioyek — a PDF reader designed for reading research papers and technical books (Qt5 + mupdf)"
    license = "GPL-3.0"
    homepage = "https://github.com/ahrm/sioyek"
    url = "https://github.com/ahrm/sioyek"

    # TEMPLATE = app：GUI 应用程序（非库），无消费方库目标
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # qt5-qtbase/5.15.2 为 -no-widgets 构建（无 Qt5Widgets），sioyek 的
        # .pro 声明 QT += widgets，须依赖启用 Widgets 的 5.15.2.2。
        self.requires("qt5-qtbase/5.15.2.2")
        # mupdf 静态 .a bundle：include/ 头文件 + lib/*.a（R26：静态链接）
        self.requires("mupdf/1.25.1")
        # .pro unix 分支 LIBS 含 -lz（synctex 使用）；用与 qtbase 链相同的
        # zlib/1.3.1（graph explain 证实：本图无 ffmpeg 钻石冲突，若按 baka
        # override 到 1.3.1.1 会改变 qtbase package_id、触发 qtbase 源码重编）
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: settings.os 判断必须 in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"sioyek only supports Linux and OHOS, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def _fix_qtbase_paths(self, qtbase_pkg):
        """qtbase 包内 bin/qt.conf 与 mkspecs/*/*.pri 记录的是构建时目录
        （conan 缓存清理后已消失），qmake 据此读不到 modules/mkspecs，
        报 Unknown module(s) in QT: core gui ...。参照 qt5-qtsvg 先例，
        把两处路径改写为 qtbase 实际 package 目录。"""
        qt_conf = os.path.join(qtbase_pkg, "bin", "qt.conf")
        if os.path.isfile(qt_conf):
            with open(qt_conf, "w", encoding="utf-8") as f:
                f.write(
                    "[EffectivePaths]\n"
                    "Prefix=..\n"
                    "[DevicePaths]\n"
                    f"Prefix={qtbase_pkg}\n"
                    "[Paths]\n"
                    f"Prefix={qtbase_pkg}\n"
                    f"HostPrefix={qtbase_pkg}\n"
                    "Sysroot=\n"
                    "SysrootifyPrefix=false\n"
                    "TargetSpec=linux-clang\n"
                    "HostSpec=linux-clang\n"
                )
        build_dir_pattern = re.compile(r"(/[^\s]*/\.conan2/p/b/qt5-q[0-9a-f]+/b)")
        for modules_dir_name in ("modules", "modules-inst"):
            modules_dir = os.path.join(qtbase_pkg, "mkspecs", modules_dir_name)
            if not os.path.isdir(modules_dir):
                continue
            for pri_file in os.listdir(modules_dir):
                if not pri_file.endswith(".pri"):
                    continue
                pri_path = os.path.join(modules_dir, pri_file)
                with open(pri_path, "r", encoding="utf-8") as f:
                    content = f.read()
                fixed = build_dir_pattern.sub(qtbase_pkg, content)
                if fixed != content:
                    with open(pri_path, "w", encoding="utf-8") as f:
                        f.write(fixed)

    def build(self):
        build_env = Environment()
        qtbase = self.dependencies["qt5-qtbase"]
        mupdf = self.dependencies["mupdf"]
        zlib = self.dependencies["zlib"]
        qmake_path = os.path.join(qtbase.package_folder, "bin", "qmake")
        if not os.path.exists(qmake_path):
            raise ConanInvalidConfiguration(
                f"qt5-qtbase 包内未找到 qmake: {qmake_path}"
            )
        # 编译器环境（clang 工具链，与 CI profile 一致；R33：显式注入，
        # 不依赖 release worker 的 shell 环境变量）
        build_env.define("CC", "/data/service/hnp/bin/clang")
        build_env.define("CXX", "/data/service/hnp/bin/clang++")
        # qmake 定位 qtbase 自身 modules/mkspecs（qt.conf/.pri 路径修复）
        build_env.prepend_path("PATH", os.path.join(qtbase.package_folder, "bin"))
        build_env.append_path("LD_LIBRARY_PATH", os.path.join(qtbase.package_folder, "lib"))
        build_env.define("QTDIR", qtbase.package_folder)
        self._fix_qtbase_paths(qtbase.package_folder)
        # 链接期：-lz 由 LIBRARY_PATH 解析（clang 识别；单路径无需拼接）。
        # mupdf 的 .a 不走 -l 查找 —— 经 qmake 命令行变量 MUPDF_LIBS 以绝对
        # 路径注入（.pro 的 OHOS 分支 LIBS += $$MUPDF_LIBS），避免
        # -lmupdf 与系统同名库解析歧义，并精确控制四个 .a 的链接顺序。
        mupdf_libs = " ".join(
            os.path.join(mupdf.package_folder, "lib", f"lib{name}.a")
            for name in ("mupdf", "mupdf-third", "mupdf-pkcs7", "mupdf-threads")
        )
        for lib in mupdf_libs.split():
            if not os.path.exists(lib):
                raise ConanInvalidConfiguration(f"mupdf 包内缺少静态库: {lib}")
        build_env.define("LIBRARY_PATH", os.path.join(zlib.package_folder, "lib"))
        with build_env.vars(self).apply():
            jobs = 2  # 本环境 make -j 并行报 jobserver mkfifo 错误，用 -j2
            # qmake 直调（in-source build，参照 qt5-qtx11extras/baka 先例）：
            # -spec linux-clang 匹配 clang 工具链；QMAKE_STRIP="" 防 strip
            # （OHOS 加载器拒绝 stripped ELF）；CONFIG+=non_portable 启用
            # NON_PORTABLE 便携布局（prefs/keys/shaders/tutorial 从可执行
            # 文件同级目录解析，main.cpp configure_paths() 的 parent_path 分支）
            self.run(
                f'cd "{self.source_folder}" && '
                f'"{qmake_path}" pdf_viewer_build_config.pro '
                f"-spec linux-clang CONFIG+=non_portable "
                f'QMAKE_STRIP="" "MUPDF_LIBS={mupdf_libs}" '
                f'"INCLUDEPATH+={os.path.join(mupdf.package_folder, "include")} '
                f'{os.path.join(zlib.package_folder, "include")}"'
            )
            self.run(
                f'cd "{self.source_folder}" && make -j{jobs} QMAKE_STRIP=""'
            )

    def package(self):
        # in-source build 且 .pro 未设 DESTDIR → 可执行文件位于源码目录
        exe = os.path.join(self.source_folder, "sioyek")
        if not os.path.isfile(exe):
            raise ConanInvalidConfiguration(f"构建产物缺失: {exe}")
        bin_dir = os.path.join(self.package_folder, "bin")
        copy(self, "sioyek", src=self.source_folder, dst=bin_dir, keep_path=False)
        # NON_PORTABLE 便携布局：配置/教程/着色器置于可执行文件同级目录
        # （main.cpp configure_paths(): default_config_path = parent_path/
        #   prefs.config；shader_path = parent_path/shaders）
        pdf_viewer_dir = os.path.join(self.source_folder, "pdf_viewer")
        copy(self, "prefs.config", src=pdf_viewer_dir, dst=bin_dir)
        copy(self, "keys.config", src=pdf_viewer_dir, dst=bin_dir)
        copy(self, "tutorial.pdf", src=self.source_folder, dst=bin_dir)
        copy(self, "shaders/*", src=pdf_viewer_dir,
             dst=os.path.join(bin_dir, "shaders"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # 二进制应用（TEMPLATE=app），无消费方库目标
        self.cpp_info.bindirs = ["bin"]
