#!/usr/bin/env python3
"""Conan recipe for qtserialport-opensource-src 5.15.15 on OpenHarmony PC.

适配方式与仓库内已通过 CI 的 Qt5 模块先例保持一致
(qt5-qtdeclarative/5.15.2、qt5-qtcharts/5.15.2.1，同样依赖
qt5-qtbase/5.15.2.2)：

qt5-qtbase 制品仓包内的 bin/qt.conf 与 mkspecs/modules/*.pri 残留了
原构建机的 conan 缓存绝对路径(~/.conan2/p/b/qt5-qXXXX/b)，在任何
其他缓存位置(如 CI 的 ~/.cache/conan2)均为悬空路径，导致 qmake 报
"Unknown module(s) in QT: core-private"。本配方在 build() 中按先例
重写这些文件指向当前包目录后再调用 qmake。
"""
import os
import re
import shlex

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class QtserialportOpensourceSrcConan(ConanFile):
    name = "qtserialport-opensource-src"
    version = "5.15.15"
    description = "Qt5 SerialPort module for HarmonyOS PC"
    license = "LGPL-3.0-only OR GPL-3.0-only"
    homepage = "https://doc.qt.io/qt-5/qtserialport-index.html"
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qt5-qtbase/5.15.2.2")

    def layout(self):
        basic_layout(self, src_folder=".")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name}/{self.version} only supports Linux and OHOS, "
                f"got {self.settings.os}"
            )

    def source(self):
        source_data = self.conan_data["sources"]
        urls = source_data["url"]
        if isinstance(urls, str):
            urls = [urls]
        for url in urls:
            try:
                get(self, url=url, sha256=source_data["sha256"], strip_root=True)
                return
            except ConanException as error:
                self.output.warning(f"Failed to download from {url}: {error}")
        raise ConanInvalidConfiguration("Unable to download source from all mirrors")

    def _fix_qtbase_paths(self, qtbase_pkg):
        """Fix qt5-qtbase package's qt.conf and .pri files to use the package
        directory instead of the original build directory (relocatability).

        先例: qt5-qtdeclarative/5.15.2 与 qt5-qtsvg/5.15.2.1 的同名方法。
        """
        # Fix qt.conf
        qt_conf = os.path.join(qtbase_pkg, "bin", "qt.conf")
        if os.path.isfile(qt_conf):
            with open(qt_conf, "w", encoding="utf-8") as f:
                f.write(
                    "[EffectivePaths]\n"
                    "Prefix=..\n"
                    f"[DevicePaths]\n"
                    f"Prefix={qtbase_pkg}\n"
                    f"[Paths]\n"
                    f"Prefix={qtbase_pkg}\n"
                    f"HostPrefix={qtbase_pkg}\n"
                    "Sysroot=\n"
                    "SysrootifyPrefix=false\n"
                    "TargetSpec=linux-clang\n"
                    "HostSpec=linux-clang\n"
                )

        # Fix .pri files that reference the build directory
        build_dir_pattern = re.compile(
            r"(/[^\s]*/\.conan2/p/b/qt5-q[0-9a-f]+/b)"
        )
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
                fixed_content = build_dir_pattern.sub(qtbase_pkg, content)
                if fixed_content != content:
                    with open(pri_path, "w", encoding="utf-8") as f:
                        f.write(fixed_content)

    def build(self):
        apply_conandata_patches(self)
        qtbase = self.dependencies["qt5-qtbase"]
        qtbase_pkg = qtbase.package_folder
        self._fix_qtbase_paths(qtbase_pkg)

        qmake = os.path.join(qtbase_pkg, "bin", "qmake")
        if not os.path.isfile(qmake):
            raise ConanException(
                "qt5-qtbase/5.15.2.2 does not provide the required bin/qmake tool"
            )

        src = self.source_folder
        jobs = self.conf.get("tools.build:jobs", default=2, check_type=int)

        build_env = Environment()
        build_env.define("QTDIR", qtbase_pkg)
        build_env.prepend_path("PATH", os.path.join(qtbase_pkg, "bin"))
        build_env.append_path("LD_LIBRARY_PATH", os.path.join(qtbase_pkg, "lib"))
        # 让 tests/auto 下的 qmake 能解析刚构建的 serialport 模块
        # (构建树内 mkspecs/modules/qt_lib_serialport.pri)
        build_env.append_path("QMAKEMODULES", os.path.join(src, "mkspecs", "modules"))

        with build_env.vars(self).apply():
            self.run(
                f'cd "{src}" && {shlex.quote(qmake)} -spec linux-clang '
                f"qtserialport.pro"
            )
            # QMAKE_STRIP="": OHOS loader 拒绝被 strip 的 ELF
            self.run(f'cd "{src}" && make -j{jobs} QMAKE_STRIP=""')

            # 上游测试构建 (R51): tests/auto/{qserialport,qserialportinfo}
            # 依赖物理串口对 (QTEST_SERIALPORT_SENDER/RECEIVER 环境变量)，
            # 无硬件时 initTestCase 会 QSKIP，不作为包构建的失败条件。
            test_bins = []
            for test_name in ("qserialport", "qserialportinfo"):
                test_dir = os.path.join(src, "tests", "auto", test_name)
                self.run(
                    f'cd "{test_dir}" && {shlex.quote(qmake)} -spec linux-clang'
                )
                self.run(f'cd "{test_dir}" && make -j{jobs} QMAKE_STRIP=""')
                test_bin = os.path.join(test_dir, f"tst_{test_name}")
                if os.path.isfile(test_bin):
                    test_bins.append(test_bin)

        # 上游测试运行 (R51): 原生环境运行；无物理串口对时
        # initTestCase QSKIP 跳过全部用例（QtTest 退出码 0），真实
        # 失败可阻断构建
        if can_run(self):
            test_env = Environment()
            test_env.append_path("LD_LIBRARY_PATH", os.path.join(qtbase_pkg, "lib"))
            test_env.append_path("LD_LIBRARY_PATH", os.path.join(src, "lib"))
            with test_env.vars(self).apply():
                for test_bin in test_bins:
                    self.run(f'"{test_bin}"')

    def package(self):
        src = self.source_folder
        pkg = self.package_folder

        # Libraries (unstripped)
        copy(self, "*.so*", src=os.path.join(src, "lib"),
             dst=os.path.join(pkg, "lib"), keep_path=False)
        copy(self, "*.prl", src=os.path.join(src, "lib"),
             dst=os.path.join(pkg, "lib"), keep_path=False)
        if os.path.isdir(os.path.join(src, "lib", "pkgconfig")):
            copy(self, "*.pc", src=os.path.join(src, "lib", "pkgconfig"),
                 dst=os.path.join(pkg, "lib", "pkgconfig"), keep_path=False)

        # HMDFS 拷贝可能丢失符号链接，显式重建 .so 链接链
        real_so = "libQt5SerialPort.so.5.15.15"
        so_path = os.path.join(pkg, "lib", real_so)
        if os.path.exists(so_path):
            for link_name in ("libQt5SerialPort.so", "libQt5SerialPort.so.5",
                              "libQt5SerialPort.so.5.15"):
                link_path = os.path.join(pkg, "lib", link_name)
                if os.path.lexists(link_path):
                    os.remove(link_path)
                os.symlink(real_so, link_path)

        # Headers: syncqt 转发头 (include/) + 实际头文件 (src/，转发头引用)
        copy(self, "*", src=os.path.join(src, "include"),
             dst=os.path.join(pkg, "include"), keep_path=True)
        copy(self, "*.h", src=os.path.join(src, "src"),
             dst=os.path.join(pkg, "src"), keep_path=True)

        # qmake 模块 .pri (含 modules-inst)，供 qmake 消费方通过
        # QMAKEMODULES 使用；重写其中残留的构建树路径为本包目录
        mkspecs_src = os.path.join(src, "mkspecs")
        if os.path.isdir(mkspecs_src):
            copy(self, "*", src=mkspecs_src,
                 dst=os.path.join(pkg, "mkspecs"), keep_path=True)
            build_tree_pattern = re.compile(re.escape(src))
            for modules_dir_name in ("modules", "modules-inst"):
                modules_dir = os.path.join(pkg, "mkspecs", modules_dir_name)
                if not os.path.isdir(modules_dir):
                    continue
                for pri_file in os.listdir(modules_dir):
                    if not pri_file.endswith(".pri"):
                        continue
                    pri_path = os.path.join(modules_dir, pri_file)
                    with open(pri_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    fixed = build_tree_pattern.sub(pkg, content)
                    if fixed != content:
                        with open(pri_path, "w", encoding="utf-8") as f:
                            f.write(fixed)

        # CMake config (Qt5SerialPortConfig.cmake 基于 CMAKE_CURRENT_LIST_DIR
        # 相对定位，可重定位)
        cmake_src = os.path.join(src, "lib", "cmake")
        if os.path.isdir(cmake_src):
            copy(self, "*", src=cmake_src,
                 dst=os.path.join(pkg, "lib", "cmake"), keep_path=True)

    def package_info(self):
        self.cpp_info.libdirs = ["lib"]
        serialport = self.cpp_info.components["Qt5SerialPort"]
        serialport.libs = ["Qt5SerialPort"]
        serialport.includedirs = ["include", "include/QtSerialPort"]
        serialport.requires = ["qt5-qtbase::Qt5Core"]
        serialport.set_property("cmake_file_name", "Qt5SerialPort")
        serialport.set_property("cmake_target_name", "Qt5::SerialPort")
