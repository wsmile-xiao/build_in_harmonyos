#!/usr/bin/env python3
"""Conan recipe for qt5-qtmultimedia 5.15.2 on OpenHarmony PC.

Qt5 Multimedia module (QtMultimedia/QtMultimediaWidgets) built with qmake
from the qt5-qtbase package.  Follows the established qt5-qtcharts pattern:
a private writable Qt prefix mirrors qtbase (symlinks + rewritten mkspecs),
qmake builds from it, and `make install` stages into an INSTALL_ROOT inside
the build folder before relocation into the package.
"""
import os
import re
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    get, apply_conandata_patches, export_conandata_patches,
)
from conan.tools.layout import basic_layout


class Qt5QtmultimediaConan(ConanFile):
    name = "qt5-qtmultimedia"
    version = "5.15.2"
    description = "Qt5 Multimedia module (QtMultimedia/QtMultimediaWidgets) for OpenHarmony"
    license = "LGPL-3.0"
    homepage = "https://www.qt.io/"
    url = ""

    settings = "os", "compiler", "build_type", "arch"
    package_type = "shared-library"

    _BUILD_DIR_PATTERN = re.compile(
        r"(/[^\s]*/(?:\.cache/)?\.?conan2/p/b/qt5-q[0-9a-f]+/b)"
    )

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
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
            except Exception as error:  # noqa: BLE001
                self.output.warning(f"Failed to download source from {url}: {error}")
        raise ConanInvalidConfiguration("Unable to download source from all mirrors")

    def _rewrite_module_files(self, mkspecs_dir, target_pkg_dir):
        build_dir_pattern = self._BUILD_DIR_PATTERN
        for modules_dir_name in ("modules", "modules-inst"):
            modules_dir = os.path.join(mkspecs_dir, modules_dir_name)
            if not os.path.isdir(modules_dir):
                continue
            for pri_file in os.listdir(modules_dir):
                if not pri_file.endswith(".pri"):
                    continue
                pri_path = os.path.join(modules_dir, pri_file)
                with open(pri_path, "r", encoding="utf-8") as f:
                    content = f.read()
                fixed = build_dir_pattern.sub(target_pkg_dir, content)
                if fixed != content:
                    with open(pri_path, "w", encoding="utf-8") as f:
                        f.write(fixed)

    def _build_qt_tree(self, qtbase_pkg):
        qt_root = os.path.join(self.build_folder, "qt-prefix")
        if os.path.isdir(qt_root):
            shutil.rmtree(qt_root)
        os.makedirs(qt_root)
        for entry in os.listdir(qtbase_pkg):
            if entry in ("bin", "mkspecs"):
                continue
            os.symlink(os.path.join(qtbase_pkg, entry), os.path.join(qt_root, entry))
        bin_src = os.path.join(qtbase_pkg, "bin")
        bin_dst = os.path.join(qt_root, "bin")
        os.makedirs(bin_dst)
        for entry in os.listdir(bin_src):
            if entry == "qt.conf":
                continue
            os.symlink(os.path.join(bin_src, entry), os.path.join(bin_dst, entry))
        with open(os.path.join(bin_dst, "qt.conf"), "w", encoding="utf-8") as f:
            f.write(
                "[EffectivePaths]\n"
                "Prefix=..\n"
                "[DevicePaths]\n"
                f"Prefix={qt_root}\n"
                "[Paths]\n"
                f"Prefix={qt_root}\n"
                f"HostPrefix={qt_root}\n"
                "Sysroot=\n"
                "SysrootifyPrefix=false\n"
                "TargetSpec=linux-clang\n"
                "HostSpec=linux-clang\n"
            )
        mkspecs_dst = os.path.join(qt_root, "mkspecs")
        shutil.copytree(os.path.join(qtbase_pkg, "mkspecs"), mkspecs_dst, symlinks=True)
        self._rewrite_module_files(mkspecs_dst, qtbase_pkg)
        return qt_root

    def _qmake_env(self, qt_root, qtbase_pkg):
        build_env = Environment()
        build_env.define("QTDIR", qt_root)
        build_env.prepend_path("PATH", os.path.join(qt_root, "bin"))
        build_env.append("LD_LIBRARY_PATH", os.path.join(qtbase_pkg, "lib"))
        return build_env

    def build(self):
        apply_conandata_patches(self)
        qtbase = self.dependencies["qt5-qtbase"]
        qt_root = self._build_qt_tree(qtbase.package_folder)
        qmake = os.path.join(qt_root, "bin", "qmake")
        if not os.path.isfile(qmake):
            raise ConanException("qt5-qtbase does not provide bin/qmake")
        build_env = self._qmake_env(qt_root, qtbase.package_folder)
        with build_env.vars(self).apply():
            self.run(
                f'cd "{self.source_folder}" && {shlex.quote(qmake)} -spec linux-clang qtmultimedia.pro'
            )
            jobs = self.conf.get("tools.build:jobs", default=4, check_type=int)
            self.run(f'cd "{self.source_folder}" && make -j{jobs} QMAKE_STRIP=""')

    def package(self):
        qtbase_pkg = self.dependencies["qt5-qtbase"].package_folder
        install_root = os.path.join(self.build_folder, "__install_root")
        if os.path.isdir(install_root):
            shutil.rmtree(install_root)
        os.makedirs(install_root)
        qt_root = os.path.join(self.build_folder, "qt-prefix")
        if not os.path.isdir(qt_root):
            qt_root = self._build_qt_tree(qtbase_pkg)
        build_env = self._qmake_env(qt_root, qtbase_pkg)
        with build_env.vars(self).apply():
            self.run(
                f'cd "{self.source_folder}" && make install '
                f'INSTALL_ROOT={shlex.quote(install_root)} STRIP=true'
            )
        staged = os.path.join(install_root, qt_root.lstrip(os.sep))
        if not os.path.isdir(staged):
            raise ConanException(
                f"make install did not stage anything under {staged}"
            )
        moved = []
        for sub in ("lib", "include", "mkspecs", "plugins", "bin", "qml"):
            src_dir = os.path.join(staged, sub)
            if not os.path.isdir(src_dir):
                continue
            shutil.copytree(src_dir, os.path.join(self.package_folder, sub),
                            symlinks=True, dirs_exist_ok=True)
            moved.append(sub)
        if "lib" not in moved:
            raise ConanException(f"incomplete Qt prefix (got: {moved})")
        shutil.rmtree(install_root, ignore_errors=True)

        # Rewrite stale build-dir references in the packaged .prl/.la/.pc
        qt_prefix_dir = os.path.join(self.build_folder, "qt-prefix")
        own_build_dir = self.build_folder.rstrip(os.sep)
        build_root = os.path.dirname(own_build_dir)
        source_dir = self.source_folder.rstrip(os.sep)
        for root, _dirs, files in os.walk(self.package_folder):
            for name in files:
                path = os.path.join(root, name)
                if not name.endswith((".prl", ".la", ".pc")):
                    continue
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                except (UnicodeDecodeError, OSError):
                    continue
                original = content
                for stale in sorted(
                    {qt_prefix_dir, own_build_dir, source_dir, build_root}, key=len, reverse=True
                ):
                    content = content.replace(stale, self.package_folder)
                if content != original:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(content)

    def package_info(self):
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include", "include/QtMultimedia", "include/QtMultimediaWidgets"]
        self.cpp_info.libs = ["Qt5Multimedia", "Qt5MultimediaWidgets"]
        self.cpp_info.requires = ["qt5-qtbase::Qt5Core", "qt5-qtbase::Qt5Gui",
                                  "qt5-qtbase::Qt5Network", "qt5-qtbase::Qt5Widgets"]
        self.cpp_info.set_property("cmake_file_name", "Qt5Multimedia")
        self.cpp_info.set_property("cmake_target_name", "Qt5::Multimedia")
