#!/usr/bin/env python3
"""Conan recipe — qconf 2.5（QConf，qmake 工程的 configure 脚本生成器，Qt5 控制台工具）。

上游: https://github.com/psi-im/qconf （tag v2.5，a06a3ca）
构建系统: qmake（qconf.pro，in-source build）

依赖（W0 依赖发布检查确认已发布）:
- QT += core xml（qconf.pro `QT -= gui` / `QT += xml` / `CONFIG += console`）
  → qt5-qtbase/5.15.2.2，提供 Qt5Core + Qt5Xml 与 qmake/moc/rcc
  传递依赖: zlib/1.3.1、dbus/1.14.10 → expat/2.8.2

运行期数据: qconf 通过 QCoreApplication::applicationDirPath() 做「就地（in-place）」
检测（appdir 下需同时存在 conf/ 与 modules/），否则回退到编译期 DATADIR 或 ./conf。
因此本配方把上游 conf/ 与 modules/ 一并装到 bin/ 下，使包自包含、与 cwd 无关。

无 X11 依赖: v2.5 默认 conf.qt4=true 走 conf4.* （QT5，无 gui/x11）；Qt3 遗留
conf/conf.pro 仅在 .qc 声明 <qt3> 时启用。
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

# qt5-qtbase 包内 mkspecs/modules/*.pri 记录的是**构建期**绝对路径
# （<builder>/p/b/<hash>/b 下的 mkspecs/modules-inst、bin/include/lib，以及
# QT_TOOL.rcc.binary 等），构建目录已不存在：qmake 会报
# "Cannot read .../modules-inst/qt_lib_core.pri"（QT += core 解析失败）、
# 生成的 Makefile 还会把 <stale>/bin/rcc 写成 qrc 的依赖而 make 直接失败。
# 因此把 modules/*.pri 复制到可写目录，逐行把构建期 conan 私有前缀改写为
# 真实 package 目录（<conan_home>/p/<hash>/p），再用 QMAKEMODULES 暴露给 qmake。
_STALE_PREFIX_RE = re.compile(r"/[^\s\"'()]*?/p/b/[^/\s\"'()]+/[bp](?=/|$|\s|\"|')")


class QconfConan(ConanFile):
    name = "qconf"
    version = "2.5"
    description = "QConf — a nice configure script generator for qmake-based projects (Qt5 console tool)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/psi-im/qconf"
    url = "https://github.com/psi-im/qconf"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # qconf 只用 Qt5Core（容器/文件/进程）与 Qt5Xml（解析 .qc 的 QDomDocument）
        # 5.15.2.2 为启用 Widgets/Xml 的完整构建（生态主流，102 个配方采用）
        self.requires("qt5-qtbase/5.15.2.2")

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: settings.os 判断必须 in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"qconf only supports Linux and OHOS, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def _setup_qmake_modules(self, build_env, qtbase_folder):
        """修复 qtbase 模块 .pri 的构建期绝对路径，并通过 QMAKEMODULES 暴露给 qmake。"""
        modules_dir = os.path.join(self.build_folder, "qmake-modules", "modules")
        os.makedirs(modules_dir, exist_ok=True)
        src_dir = os.path.join(qtbase_folder, "mkspecs", "modules")

        for name in sorted(os.listdir(src_dir)):
            if not name.endswith(".pri"):
                continue
            with open(os.path.join(src_dir, name), "r", encoding="utf-8",
                      errors="replace") as fh:
                content = fh.read()
            with open(os.path.join(modules_dir, name), "w", encoding="utf-8") as fh:
                fh.write(_STALE_PREFIX_RE.sub(qtbase_folder, content))

        build_env.define("QMAKEMODULES", modules_dir)

    def _write_qt_conf(self, qtbase_folder):
        """生成指向真实 package 目录的 qt.conf 并用 qmake -qtconf 加载。

        qt5-qtbase 包内 bin/qt.conf 的 [Paths] Prefix 记录的是**构建期**目录，
        导致 QT_INSTALL_BINS 解析到已消失路径（`<stale>/bin/rcc` 报
        "inaccessible or not found"），QT_INSTALL_LIBS 也把失效路径写进产物 RUNPATH。
        用修正后的 qt.conf 覆盖 Prefix/HostPrefix 即同时修好 rcc/moc/uic 与 RUNPATH。
        注意：不能带 [EffectivePaths] Prefix=.. （会让 -qtconf 找不到 mkspec）。
        """
        qt_conf = os.path.join(self.build_folder, "qt.conf")
        with open(qt_conf, "w", encoding="utf-8") as fh:
            fh.write(
                "[Paths]\n"
                f"Prefix={qtbase_folder}\n"
                f"HostPrefix={qtbase_folder}\n"
                "Sysroot=\n"
            )
        return qt_conf

    def build(self):
        # conan 2.29 无 conan.tools.qmake（只有 cmake/meson），用 self.run 直接调用
        # qmake + make（参照 qt5-qtx11extras / baka 先例）
        qtbase = self.dependencies["qt5-qtbase"]
        qmake = os.path.join(qtbase.package_folder, "bin", "qmake")
        if not os.path.exists(qmake):
            raise ConanInvalidConfiguration(f"qt5-qtbase 包内未找到 qmake: {qmake}")

        qt_conf = self._write_qt_conf(qtbase.package_folder)

        build_env = Environment()
        # qmake/moc 本身链接 libQt5Core，运行期亦需 Qt 库目录（conanrun 环境同样提供）
        build_env.define("LD_LIBRARY_PATH", os.path.join(qtbase.package_folder, "lib"))
        self._setup_qmake_modules(build_env, qtbase.package_folder)

        # qmake 仍会从 mkspecs/modules（QT_MODULE_*_BASE 为构建期路径）解析出
        # QMAKE_RCC/MOC/UIC，命令行赋值优先级最高，显式钉到 package 的 bin/
        qt_bin = os.path.join(qtbase.package_folder, "bin")
        tool_overrides = " ".join(
            f'"{var}={os.path.join(qt_bin, tool)}"'
            for var, tool in (("QMAKE_RCC", "rcc"),
                              ("QMAKE_MOC", "moc"),
                              ("QMAKE_UIC", "uic"))
        )

        with build_env.vars(self).apply():
            # 本环境 make -j>1 触发 jobserver mkfifo（HMDFS 不允许 mkfifo），用 -j1
            # QMAKE_STRIP 置空：OHOS 加载器拒绝 stripped ELF
            self.run(
                f'cd "{self.source_folder}" && '
                f'"{qmake}" -qtconf "{qt_conf}" qconf.pro -spec linux-clang {tool_overrides}',
                env="conanbuild",
            )
            self.run(
                f'cd "{self.source_folder}" && make -j1 QMAKE_STRIP=',
                env="conanbuild",
            )

    def package(self):
        src = self.source_folder
        # 二进制
        copy(self, "qconf", src=src, dst=os.path.join(self.package_folder, "bin"),
             keep_path=False)
        # 运行期数据：qconf 以 applicationDirPath()/conf + /modules 做就地检测；
        # copy 保留匹配到的相对路径（conf/xxx → <pkg>/bin/conf/xxx），故 dst 为 bin/
        for data_dir in ("conf", "modules"):
            copy(self, f"{data_dir}/*", src=src,
                 dst=os.path.join(self.package_folder, "bin"))
        copy(self, "COPYING", src=src, dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
