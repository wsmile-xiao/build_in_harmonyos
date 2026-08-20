#!/usr/bin/env python3
"""Conan recipe for qt5-qtdeclarative 5.15.2 on OpenHarmony PC.

QtDeclarative provides QtQml/QtQuick modules. It is a build-time
prerequisite for QML modules such as qt5-qtgraphicaleffects and
QtQuick3D in qt5-qt3d.
"""
import os
import re
import shlex

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


class Qt5QtDeclarativeConan(ConanFile):
    name = "qt5-qtdeclarative"
    version = "5.15.2"
    description = "Qt5 QML/Quick modules (QtQml, QtQuick) for OpenHarmony"
    license = "LGPL-3.0"
    homepage = "https://www.qt.io/"

    settings = "os", "compiler", "build_type", "arch"
    package_type = "shared-library"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # qmake 工具与 Qt5 基础库由 qt5-qtbase 提供
        self.requires("qt5-qtbase/5.15.2.2")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name} only supports Linux and OHOS, got {self.settings.os}"
            )

    def source(self):
        source_data = self.conan_data["sources"][self.version]
        urls = source_data["url"]
        if isinstance(urls, str):
            urls = [urls]
        for url in urls:
            try:
                get(self, url=url, sha256=source_data.get("sha256", ""), strip_root=True)
                return
            except ConanException as error:
                self.output.warning(f"Failed to download source from {url}: {error}")
        raise ConanInvalidConfiguration("Unable to download source from all mirrors")

    def _fix_qtbase_paths(self, qtbase_pkg):
        """Fix qt5-qtbase package's qt.conf and .pri files to use the package
        directory instead of the original build directory (relocatability)."""
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
        qtbase = self.dependencies["qt5-qtbase"]
        self._fix_qtbase_paths(qtbase.package_folder)
        qmake = os.path.join(qtbase.package_folder, "bin", "qmake")
        if not os.path.isfile(qmake):
            raise ConanException(
                "qt5-qtbase/5.15.2.1 does not provide the required bin/qmake tool"
            )
        build_env = Environment()
        build_env.define("QTDIR", qtbase.package_folder)
        build_env.prepend_path("PATH", os.path.join(qtbase.package_folder, "bin"))
        build_env.append("LD_LIBRARY_PATH", os.path.join(qtbase.package_folder, "lib"))
        with build_env.vars(self).apply():
            self.run(
                f'cd "{self.source_folder}" && {shlex.quote(qmake)} -spec linux-clang qtdeclarative.pro'
            )
            jobs = self.conf.get("tools.build:jobs", default=4, check_type=int)
            self.run(f'cd "{self.source_folder}" && make -j{jobs} QMAKE_STRIP=""')

    def package(self):
        src = self.source_folder
        copy(self, "*.so*", src=os.path.join(src, "lib"),
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.prl", src=os.path.join(src, "lib"),
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        if os.path.isdir(os.path.join(src, "include")):
            copy(self, "*", src=os.path.join(src, "include"),
                 dst=os.path.join(self.package_folder, "include"), keep_path=True)
        for sub in ("plugins", "qml", "mkspecs", "src"):
            d = os.path.join(src, sub)
            if os.path.isdir(d):
                copy(self, "*", src=d,
                     dst=os.path.join(self.package_folder, sub), keep_path=True)

    def package_info(self):
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = [
            "Qt5Qml", "Qt5QmlModels", "Qt5QmlWorkerScript",
            "Qt5Quick", "Qt5QuickTest", "Qt5QuickWidgets",
            "Qt5QuickParticles", "Qt5QuickShapes",
        ]
        # QtQml/QtQuick 头文件位于 include/QtQml、include/QtQuick 等子目录，
        # 需同时暴露以支持 #include <QQmlEngine> 等
        self.cpp_info.includedirs = [
            "include",
            "include/QtQml",
            "include/QtQmlModels",
            "include/QtQuick",
            "include/QtPacketProtocol",
            "include/QtQmlDebug",
            "include/QtQuickTest",
        ]
        self.cpp_info.requires = ["qt5-qtbase::Qt5Core", "qt5-qtbase::Qt5Gui",
                                  "qt5-qtbase::Qt5Network"]
        self.cpp_info.set_property("cmake_file_name", "Qt5Qml")
        self.cpp_info.set_property("cmake_target_name", "Qt5::Qml")
