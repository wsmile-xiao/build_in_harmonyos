#!/usr/bin/env python3
"""Conan recipe for qtpositioning 5.15.2 on OpenHarmony PC.

Qt Positioning provides the QtPositioning C++ module (QGeoCoordinate,
QGeoShape family, QGeoPath/QGeoPolygon, QNmeaPositionInfoSource, position
source/area-monitor factory interfaces) and the QtPositioningQuick module
(QML API: PositionSource/Position/CoordinateAnimation) plus the
QtPositioning QML plugin and the positionpoll position plugin.

Upstream ships positioning inside the qtlocation repository (positioning
and location share one repo/tarball, source root qtlocation.pro).  This
recipe builds only the positioning sub-tree (src/3rdparty helper libs,
src/positioning, src/positioningquick, src/imports/positioning,
src/plugins/position/positionpoll); the location module and the
platform-specific position plugins (geoclue/gypsy/serialnmea/...) are out
of scope.
"""
import os
import re
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    copy,
)
from conan.tools.layout import basic_layout


class QtpositioningConan(ConanFile):
    name = "qtpositioning"
    version = "5.15.2"
    description = "Qt5 Positioning module (QtPositioning + QtPositioningQuick, QML + position plugins) for OpenHarmony"
    license = "LGPL-3.0"
    homepage = "https://www.qt.io/"

    settings = "os", "compiler", "build_type", "arch"
    package_type = "shared-library"

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # qmake 工具与 Qt5 基础库由 qt5-qtbase 提供；
        # QtQuick/Qml 由 qt5-qtdeclarative 提供（QtPositioningQuick 依赖）
        self.requires("qt5-qtbase/5.15.2.2")
        self.requires("qt5-qtdeclarative/5.15.2")

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

    def _fix_qtdecl_paths(self, qtdecl_pkg, qtbase_pkg):
        """Fix qt5-qtdeclarative .pri files to reference the correct
        package directories instead of the original build directory,
        and merge them into qt5-qtbase's mkspecs/modules."""
        # Pattern matches both .conan2 and .cache/conan2 build paths
        build_dir_pattern = re.compile(
            r"/[^\s]*/p/b/qt5-q[0-9a-f]+/b"
        )

        qtbase_modules = os.path.join(qtbase_pkg, "mkspecs", "modules")
        qtbase_modules_inst = os.path.join(qtbase_pkg, "mkspecs", "modules-inst")

        for modules_dir_name in ("modules", "modules-inst"):
            src_dir = os.path.join(qtdecl_pkg, "mkspecs", modules_dir_name)
            if not os.path.isdir(src_dir):
                continue
            for pri_file in os.listdir(src_dir):
                if not pri_file.endswith(".pri"):
                    continue
                src_path = os.path.join(src_dir, pri_file)
                with open(src_path, "r", encoding="utf-8") as f:
                    content = f.read()
                # Fix build dir references to qtdeclarative package
                fixed_content = build_dir_pattern.sub(qtdecl_pkg, content)
                # Write to qt5-qtbase's mkspecs directory
                dst_dir = qtbase_modules if modules_dir_name == "modules" else qtbase_modules_inst
                os.makedirs(dst_dir, exist_ok=True)
                dst_path = os.path.join(dst_dir, pri_file)
                with open(dst_path, "w", encoding="utf-8") as f:
                    f.write(fixed_content)

    def _materialize_shared_object_links(self, src):
        """Materialize the libFoo.so / .so.5 / .so.5.15 aliases as file
        copies.

        OHOS filesystems reject symlink creation (EPERM), while the qmake
        qt_module build emits `mv` steps that would produce a symlink
        chain libFoo.so -> libFoo.so.5 -> libFoo.so.5.15 -> libFoo.so.5.15.2
        (the -jN parallel race makes them partially fail with ignored
        errors).  Copying the real shared object under the alias names
        keeps -lFoo and the runtime soname lookup working."""
        lib_dir = os.path.join(src, "lib")
        if not os.path.isdir(lib_dir):
            return
        for entry in os.listdir(lib_dir):
            match = re.match(r"^(.*\.so)\.(\d+)\.(\d+)\.(\d+)$", entry)
            if not match:
                continue
            base, major, minor, _patch = match.groups()
            real = os.path.join(lib_dir, entry)
            for alias in (f"{base}.{major}.{minor}", f"{base}.{major}", base):
                alias_path = os.path.join(lib_dir, alias)
                if not os.path.exists(alias_path):
                    shutil.copyfile(real, alias_path)

    def _sync_forward_headers(self, src):
        """Replace syncqt forward headers with copies of the real headers.

        The qmake build's include/QtPositioning and include/QtPositioningQuick
        contain syncqt-generated forwarding headers that reference the source
        tree via relative paths like "../../src/positioning/qgeocoordinate.h".
        Those relative paths break once the package is relocated, so we copy
        the real headers from src/ over the forwarding stubs."""
        for module, src_subdir in (
            ("QtPositioning", "positioning"),
            ("QtPositioningQuick", "positioningquick"),
        ):
            include_dir = os.path.join(src, "include", module)
            module_src = os.path.join(src, "src", src_subdir)
            if not os.path.isdir(include_dir) or not os.path.isdir(module_src):
                continue
            # Public forwarding headers: <module>/<name>.h -> src/<subdir>/<name>.h
            for entry in os.listdir(include_dir):
                real = os.path.join(module_src, entry)
                dst = os.path.join(include_dir, entry)
                if entry.endswith(".h") and os.path.isfile(real):
                    shutil.copyfile(real, dst)
            # Private versioned forwarding headers:
            # <module>/5.15.2/<module>/private/<name>_p.h -> src/<subdir>/<name>_p.h
            version_dir = os.path.join(include_dir, self.version)
            if not os.path.isdir(version_dir):
                continue
            for root, _dirs, files in os.walk(version_dir):
                for entry in files:
                    if not entry.endswith(".h"):
                        continue
                    real = os.path.join(module_src, entry)
                    dst = os.path.join(root, entry)
                    if os.path.isfile(real):
                        shutil.copyfile(real, dst)

    # 子项目构建顺序（对应上游 src/src.pro 的 SUBDIRS 依赖链，限定 positioning
    # 范围；location 模块与平台来源插件不在本包范围）。
    # 上游 src/plugins/position/position.pro 使用 QT_FOR_CONFIG +=
    # positioning-private + qtConfig(gypsy) 读取 configure 生成的特性文件，
    # 单子项目 qmake 构建没有 configure 产物，直接构建 positionpoll 插件本体。
    _BUILD_UNITS = (
        ("src/3rdparty/clipper", "clipper.pro"),
        ("src/3rdparty/poly2tri", "poly2tri.pro"),
        ("src/3rdparty/clip2tri", "clip2tri.pro"),
        ("src/positioning", "positioning.pro"),
        ("src/positioningquick", "positioningquick.pro"),
        ("src/imports/positioning", "positioning.pro"),
        ("src/plugins/position/positionpoll", "positionpoll.pro"),
    )

    def build(self):
        apply_conandata_patches(self)
        qtbase = self.dependencies["qt5-qtbase"]
        qtdecl = self.dependencies["qt5-qtdeclarative"]
        self._fix_qtbase_paths(qtbase.package_folder)
        qmake = os.path.join(qtbase.package_folder, "bin", "qmake")
        if not os.path.isfile(qmake):
            raise ConanException(
                "qt5-qtbase does not provide the required bin/qmake tool"
            )

        # Merge qt5-qtdeclarative .pri files into qt5-qtbase mkspecs so that
        # qtHaveModule(quick)/QT += quick resolves during qmake configure.
        self._fix_qtdecl_paths(qtdecl.package_folder, qtbase.package_folder)

        build_env = Environment()
        build_env.define("QTDIR", qtbase.package_folder)
        build_env.prepend_path("PATH", os.path.join(qtbase.package_folder, "bin"))
        build_env.append("LD_LIBRARY_PATH", os.path.join(qtbase.package_folder, "lib"))
        build_env.append("LD_LIBRARY_PATH", os.path.join(qtdecl.package_folder, "lib"))

        jobs = self.conf.get("tools.build:jobs", default=4, check_type=int)
        with build_env.vars(self).apply():
            for subdir, project in self._BUILD_UNITS:
                workdir = os.path.join(self.source_folder, subdir)
                self.run(
                    f"{shlex.quote(qmake)} -spec linux-clang {project}", cwd=workdir
                )
                self.run(f"make -j{jobs} QMAKE_STRIP=", cwd=workdir)
                # positioning 之后 positioningquick 需要 libQt5Positioning.so，
                # imports/positioning 需要 libQt5PositioningQuick.so，
                # 每步补齐 .so 别名副本保证后续链接可用。
                self._materialize_shared_object_links(self.source_folder)

        # Make include/ relocatable before packaging
        self._sync_forward_headers(self.source_folder)

    def package(self):
        src = self.source_folder

        # C++ 库：共享库（含 .so 名别名副本）、3rdparty 静态助手库、.la/.prl
        lib_dir = os.path.join(src, "lib")
        if os.path.isdir(lib_dir):
            copy(self, "*.so*", src=lib_dir,
                 dst=os.path.join(self.package_folder, "lib"), keep_path=False)
            copy(self, "*.a", src=lib_dir,
                 dst=os.path.join(self.package_folder, "lib"), keep_path=False)
            copy(self, "*.prl", src=lib_dir,
                 dst=os.path.join(self.package_folder, "lib"), keep_path=False)
            # Qt5 CMake 配置（Qt5Positioning/Qt5PositioningQuick，位于 lib/cmake）
            cmake_dir = os.path.join(lib_dir, "cmake")
            if os.path.isdir(cmake_dir):
                copy(self, "*", src=cmake_dir,
                     dst=os.path.join(self.package_folder, "lib", "cmake"), keep_path=True)

        # 头文件（QtPositioning / QtPositioningQuick；QtLocation 头不在本包范围）
        for module in ("QtPositioning", "QtPositioningQuick"):
            module_include = os.path.join(src, "include", module)
            if os.path.isdir(module_include):
                copy(self, "*", src=module_include,
                     dst=os.path.join(self.package_folder, "include", module), keep_path=True)

        # qmake 模块描述（qt_lib_positioning*.pri / qt_plugin_*.pri / qt_ext__*.pri）
        mkspecs_modules = os.path.join(src, "mkspecs", "modules")
        if os.path.isdir(mkspecs_modules):
            copy(self, "*.pri", src=mkspecs_modules,
                 dst=os.path.join(self.package_folder, "mkspecs", "modules"), keep_path=False)

        # QML 插件（QtPositioning import：PositionSource/Position/GeoShape 等）
        qml_dir = os.path.join(src, "qml")
        if os.path.isdir(qml_dir):
            copy(self, "*", src=qml_dir,
                 dst=os.path.join(self.package_folder, "qml"), keep_path=True)

        # C++ position 插件（positionpoll：QGeoAreaMonitorSource 提供者）
        plugins_dir = os.path.join(src, "plugins")
        if os.path.isdir(plugins_dir):
            copy(self, "*", src=plugins_dir,
                 dst=os.path.join(self.package_folder, "plugins"), keep_path=True)

    def package_info(self):
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["Qt5Positioning", "Qt5PositioningQuick"]
        # 公共头位于 include/QtPositioning、include/QtPositioningQuick；
        # 私有头位于 include/QtPositioning/5.15.2/QtPositioning/private/... 等
        self.cpp_info.includedirs = [
            "include",
            "include/QtPositioning",
            "include/QtPositioningQuick",
            "include/QtPositioning/5.15.2",
            "include/QtPositioning/5.15.2/QtPositioning",
            "include/QtPositioningQuick/5.15.2",
            "include/QtPositioningQuick/5.15.2/QtPositioningQuick",
        ]
        self.cpp_info.requires = [
            "qt5-qtbase::Qt5Core",
            "qt5-qtbase::Qt5Gui",
            "qt5-qtdeclarative::qt5-qtdeclarative",
        ]
        self.cpp_info.set_property("cmake_file_name", "Qt5Positioning")
        self.cpp_info.set_property("cmake_target_name", "Qt5::Positioning")
