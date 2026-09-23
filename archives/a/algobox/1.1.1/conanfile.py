#!/usr/bin/env python3
"""Conan recipe for AlgoBox 1.1.1 on HarmonyOS PC.

AlgoBox is a Qt qmake desktop application. The recipe replaces the WebEngine
view and obsolete WebChannel/Core5Compat hooks with local Qt Widgets fallbacks
so the package can build with registry-published Qt modules only.
"""

import os
import shutil
import stat
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class AlgoboxConan(ConanFile):
    name = "algobox"
    version = "1.1.1"
    description = "AlgoBox educational algorithm editor and runner"
    license = "GPL-2.0-or-later"
    homepage = "https://www.xm1math.net/algobox/"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires(
            "qtbase/6.11.1",
            transitive_headers=True,
            transitive_libs=True,
        )

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "algobox supports Linux-compatible Qt targets only"
            )
        if self.settings.os == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "algobox/1.1.1 is prepared for HarmonyOS PC aarch64"
            )

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        self._qt_environment().vars(self).save_script("conanbuild_algobox_qt")

    def build(self):
        apply_conandata_patches(self)
        qmake = self._qmake_executable()
        qmake_args = [qmake]
        if self.settings.os == "OHOS":
            qmake_args.extend(["-spec", "harmonyos-clang"])
        qmake_args.extend(
            [
                "CONFIG+=release",
                "CONFIG-=debug",
                "COMPILEUSB=no",
                "PREFIX=/",
                "DESKTOPDIR=/share/applications",
                "ICONDIR=/share/pixmaps",
                "MIMEDIR=/share/mime/packages",
                "NO_APPDATA=1",
                "DEFINES+=ALGOBOX_NO_WEBENGINE",
                "algobox.pro",
            ]
        )
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        if compilers.get("c"):
            qmake_args.insert(-1, "QMAKE_CC={}".format(compilers["c"]))
        if compilers.get("cpp"):
            qmake_args.insert(-1, "QMAKE_CXX={}".format(compilers["cpp"]))
        with self._qt_environment().vars(self).apply():
            subprocess.run(qmake_args, cwd=self.source_folder, check=True)
            subprocess.run(["make", "-j1"], cwd=self.source_folder, check=True)
            self.output.info(
                "Upstream AlgoBox 1.1.1 has no make check/ctest suite; "
                "test_package runs the packaged binary's CLI smoke entry."
            )

    def package(self):
        binary = os.path.join(self.source_folder, "algobox")
        if not os.path.isfile(binary):
            raise ConanInvalidConfiguration("qmake build did not produce algobox")
        bin_dir = os.path.join(self.package_folder, "bin")
        data_dir = os.path.join(self.package_folder, "share", "algobox")
        os.makedirs(bin_dir, exist_ok=True)
        os.makedirs(data_dir, exist_ok=True)
        shutil.copy2(binary, os.path.join(bin_dir, "algobox"))
        os.chmod(
            os.path.join(bin_dir, "algobox"),
            stat.S_IMODE(os.stat(os.path.join(bin_dir, "algobox")).st_mode) | 0o755,
        )

        copy(self, "qt_fr.qm", os.path.join(self.source_folder, "utilities"), data_dir)
        copy(self, "*.alg", os.path.join(self.source_folder, "ressources"), data_dir)
        copy(self, "aidealgobox.html", os.path.join(self.source_folder, "ressources"), data_dir)
        copy(self, "algobox.png", os.path.join(self.source_folder, "utilities"), os.path.join(self.package_folder, "share", "pixmaps"))
        copy(self, "algobox.desktop", os.path.join(self.source_folder, "utilities"), os.path.join(self.package_folder, "share", "applications"))
        copy(self, "x-algobox.xml", os.path.join(self.source_folder, "utilities"), os.path.join(self.package_folder, "share", "mime", "packages"))
        copy(self, "COPYING", os.path.join(self.source_folder, "utilities"), os.path.join(self.package_folder, "licenses"))
        copy(self, "license.txt", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        for dep_name in ("qtbase",):
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                self.runenv_info.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                self.runenv_info.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )

    def _qmake_executable(self):
        qtbase = self.dependencies["qtbase"].package_folder
        for name in ("qmake6", "qmake"):
            candidate = os.path.join(qtbase, "bin", name)
            if os.path.isfile(candidate):
                return candidate
        raise ConanInvalidConfiguration(
            "qtbase/6.11.1 does not provide bin/qmake6 or bin/qmake"
        )

    def _qt_environment(self):
        env = Environment()
        for dep_name in ("qtbase",):
            dep = self.dependencies.get(dep_name)
            if not dep or not dep.package_folder:
                continue
            root = dep.package_folder
            env.prepend_path("PATH", os.path.join(root, "bin"))
            env.prepend_path("LD_LIBRARY_PATH", os.path.join(root, "lib"))
            env.prepend_path("QT_PLUGIN_PATH", os.path.join(root, "plugins"))
            env.prepend_path("QMAKEPATH", root)
            env.prepend_path("QML2_IMPORT_PATH", os.path.join(root, "qml"))
        return env
