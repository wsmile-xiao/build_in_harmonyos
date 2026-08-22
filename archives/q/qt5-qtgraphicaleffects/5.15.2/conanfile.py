#!/usr/bin/env python3
"""Conan recipe for qt5-qtgraphicaleffects 5.15.2 on OpenHarmony PC.

QtGraphicalEffects provides QML visual effect plugins (blur, glow,
shadows, gradients, etc.) for Qt Quick applications. It is a QML
plugin module built with qmake, producing a QML plugin .so and
associated .qml resource files.
"""
import os
import re
import shlex

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class Qt5QtGraphicalEffectsConan(ConanFile):
    name = "qt5-qtgraphicaleffects"
    version = "5.15.2"
    description = "Qt5 Graphical Effects module - QML plugins for visual effects on OpenHarmony"
    license = "LGPL-3.0"
    homepage = "https://www.qt.io/"

    settings = "os", "compiler", "build_type", "arch"
    package_type = "shared-library"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
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
        import shutil

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

    def build(self):
        apply_conandata_patches(self)
        qtbase = self.dependencies["qt5-qtbase"]
        self._fix_qtbase_paths(qtbase.package_folder)
        qmake = os.path.join(qtbase.package_folder, "bin", "qmake")
        if not os.path.isfile(qmake):
            raise ConanException(
                "qt5-qtbase does not provide the required bin/qmake tool"
            )

        # Also fix qt5-qtdeclarative paths (qml plugins reference build dir)
        qtdecl = self.dependencies["qt5-qtdeclarative"]
        self._fix_qtdecl_paths(qtdecl.package_folder, qtbase.package_folder)
        qtdecl_qml = os.path.join(qtdecl.package_folder, "qml")
        if os.path.isdir(qtdecl_qml):
            pass

        build_env = Environment()
        build_env.define("QTDIR", qtbase.package_folder)
        build_env.prepend_path("PATH", os.path.join(qtbase.package_folder, "bin"))
        build_env.append("LD_LIBRARY_PATH", os.path.join(qtbase.package_folder, "lib"))
        build_env.append("LD_LIBRARY_PATH", os.path.join(qtdecl.package_folder, "lib"))

        with build_env.vars(self).apply():
            self.run(
                f'cd "{self.source_folder}" && '
                f'{shlex.quote(qmake)} -spec linux-clang qtgraphicaleffects.pro'
            )
            jobs = self.conf.get("tools.build:jobs", default=2, check_type=int)
            self.run(f'cd "{self.source_folder}" && make -j{jobs} QMAKE_STRIP=""')

    def package(self):
        src = self.source_folder

        # Copy QML plugins (the main build product)
        qml_dir = os.path.join(src, "qml")
        if os.path.isdir(qml_dir):
            copy(self, "*", src=qml_dir,
                 dst=os.path.join(self.package_folder, "qml"), keep_path=True)

        # Copy .qml resource files from src/effects/ to qml/QtGraphicalEffects/
        effects_dir = os.path.join(src, "src", "effects")
        if os.path.isdir(effects_dir):
            qml_dest = os.path.join(self.package_folder, "qml", "QtGraphicalEffects")
            copy(self, "*.qml", src=effects_dir,
                 dst=qml_dest, keep_path=False)

        # Copy libraries if any
        lib_dir = os.path.join(src, "lib")
        if os.path.isdir(lib_dir):
            copy(self, "*.so*", src=lib_dir,
                 dst=os.path.join(self.package_folder, "lib"), keep_path=False)
            copy(self, "*.prl", src=lib_dir,
                 dst=os.path.join(self.package_folder, "lib"), keep_path=False)

        # Copy plugins if any
        plugins_dir = os.path.join(src, "plugins")
        if os.path.isdir(plugins_dir):
            copy(self, "*", src=plugins_dir,
                 dst=os.path.join(self.package_folder, "plugins"), keep_path=True)

        # Copy mkspecs modules
        mkspecs_dir = os.path.join(src, "mkspecs")
        if os.path.isdir(mkspecs_dir):
            copy(self, "*", src=mkspecs_dir,
                 dst=os.path.join(self.package_folder, "mkspecs"), keep_path=True)

        # Copy cmake configs if any
        cmake_dir = os.path.join(lib_dir, "cmake") if os.path.isdir(lib_dir) else None
        if cmake_dir and os.path.isdir(cmake_dir):
            copy(self, "*", src=cmake_dir,
                 dst=os.path.join(self.package_folder, "lib", "cmake"), keep_path=True)

    def package_info(self):
        self.cpp_info.libdirs = ["lib"]

        # QtGraphicalEffects is a QML plugin module, not a traditional library.
        # The main artifact is the QML plugin .so under qml/QtGraphicalEffects/
        self.cpp_info.libs = []  # QML plugin, no traditional link library
        self.cpp_info.includedirs = []
        self.cpp_info.requires = [
            "qt5-qtbase::Qt5Core",
            "qt5-qtbase::Qt5Gui",
            "qt5-qtdeclarative::qt5-qtdeclarative",
        ]
        self.cpp_info.set_property("cmake_file_name", "Qt5GraphicalEffects")
        self.cpp_info.set_property("cmake_target_name", "Qt5::GraphicalEffects")
