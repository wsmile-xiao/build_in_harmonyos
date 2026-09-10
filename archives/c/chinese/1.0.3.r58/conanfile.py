#!/usr/bin/env python3
"""Conan recipe for Chinese Calendar 1.0.3.r58 on HarmonyOS PC."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.layout import basic_layout


class ChineseCalendarConan(ConanFile):
    name = "chinese"
    version = "1.0.3.r58"
    description = "Chinese traditional calendar desktop application for Qt"
    license = "GPL-3.0-or-later"
    homepage = "https://launchpad.net/chinese-calendar"
    url = "https://github.com/WhiredPlanck/chinese-calendar"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase-sql-dbus/6.11.1")
        self.requires("qtsvg/6.11.1")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"chinese supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        main_cpp = os.path.join(self.source_folder, "main.cpp")
        with open(main_cpp, "rb") as source_file:
            content = source_file.read()
        with open(main_cpp, "wb") as source_file:
            source_file.write(content.replace(b"\\r\\n", b"\\n"))

    def build(self):
        for patch_data in self.conan_data["patches"]:
            patch_path = os.path.join(self.export_sources_folder, patch_data["patch_file"])
            self.run(f'patch -l -p1 < "{patch_path}"', cwd=self.source_folder)

        main_cpp = os.path.join(self.source_folder, "main.cpp")
        replace_in_file(self, main_cpp, "#include <QDesktopWidget>", "")

        qtbase = self.dependencies["qtbase"]
        qmake = os.path.join(qtbase.package_folder, "bin", "qmake6")
        if not os.path.isfile(qmake):
            qmake = os.path.join(qtbase.package_folder, "bin", "qmake")
        sql_prefix = self.dependencies["qtbase-sql-dbus"].package_folder
        svg_prefix = self.dependencies["qtsvg"].package_folder
        qmakepath = os.pathsep.join([qtbase.package_folder, sql_prefix, svg_prefix])
        self.run(
            f'QMAKEPATH="{qmakepath}" '
            f'"{qmake}" chinese-calendar.pro PREFIX=/usr '
            f'INCLUDEPATH+="{os.path.join(sql_prefix, "include")}" '
            f'QMAKE_LIBDIR+="{os.path.join(sql_prefix, "lib")} {os.path.join(svg_prefix, "lib")}"',
            cwd=self.source_folder,
        )
        replace_in_file(
            self,
            os.path.join(self.source_folder, "Makefile"),
            f"{qtbase.package_folder}/lib/libQt6Svg.so",
            f"{svg_prefix}/lib/libQt6Svg.so",
        )
        replace_in_file(
            self,
            os.path.join(self.source_folder, "Makefile"),
            f"{qtbase.package_folder}/lib/libQt6Sql.so",
            f"{sql_prefix}/lib/libQt6Sql.so",
        )
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        copy(self, "chinese-calendar", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "chinese-calendar-autostart", self.source_folder, os.path.join(self.package_folder, "usr", "bin"))
        copy(self, "KylinLunar.db", self.source_folder, os.path.join(self.package_folder, "usr", "share", "chinese-calendar", "db"))
        copy(self, "*.desktop", self.source_folder, os.path.join(self.package_folder, "usr", "share", "applications"))
        copy(self, "chinese-calendar-autostart.desktop", self.source_folder, os.path.join(self.package_folder, "etc", "xdg", "autostart"))
        copy(self, "*.png", os.path.join(self.source_folder, "img"), os.path.join(self.package_folder, "usr", "share", "pixmaps"))
        copy(self, "*.png", os.path.join(self.source_folder, "skin"), os.path.join(self.package_folder, "usr", "share", "chinese-calendar", "skin"), keep_path=True)
        copy(self, "*.qss", os.path.join(self.source_folder, "skin"), os.path.join(self.package_folder, "usr", "share", "chinese-calendar", "skin"))
        copy(self, "README.md", os.path.join(self.source_folder, "skin"), os.path.join(self.package_folder, "usr", "share", "chinese-calendar", "skin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
